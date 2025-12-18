from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback when dependency isn't installed
    def load_dotenv() -> bool:
        env_path = Path(".env")
        if not env_path.exists():
            return False
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
        return True
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from components.response_bank import ResponseBank


class ClassificationResult(BaseModel):
    intent_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    slots: Dict[str, str] = Field(default_factory=dict)
    rationale: str


class IntentClassifier:
    def __init__(self, response_bank: ResponseBank, model: str = "gpt-4.1-mini", confidence_threshold: float = 0.7):
        load_dotenv()
        self.response_bank = response_bank
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = OpenAI(api_key=self.api_key) if self.api_key else None

    def has_api_key(self) -> bool:
        return self.client is not None

    def validate_connection(self) -> Tuple[str, str]:
        """Lightweight check to confirm API key presence and connectivity."""

        if not self.api_key:
            return "missing", "OPENAI_API_KEY is not configured."

        if not self.client:
            return "error", "OpenAI client is unavailable."

        try:
            self.client.models.list()
            return "ok", "API key loaded and reachable."
        except Exception as exc:  # noqa: BLE001
            return "error", f"OpenAI validation failed: {exc}"

    def _hard_rule_override(self, message: str) -> Optional[ClassificationResult]:
        lowered = message.lower()
        emergency_terms = [
            "emergency",
            "can't breathe",
            "cannot breathe",
            "blue lips",
            "call 911",
            "911",
            "go to er",
            "hospital now",
            "chest pain",
            "severe trouble breathing",
        ]
        for term in emergency_terms:
            if term in lowered:
                target_intent = "urgent_support" if "urgent_support" in self.response_bank.get_allowed_intent_ids() else "__NO_MATCH__"
                return ClassificationResult(
                    intent_id=target_intent,
                    confidence=1.0,
                    slots={},
                    rationale=f"Hard rule matched phrase '{term}'"
                )
        return None

    def _build_system_prompt(self) -> str:
        lines = [
            "You classify user RSV questions into intents and never provide medical advice.",
            "Select the best intent_id from the approved list. If nothing fits, return __NO_MATCH__.",
            "Use only the JSON schema supplied and avoid additional text.",
            "Allowed intents:"
        ]
        for intent in self.response_bank.intents:
            lines.append(
                f"- {intent['intent_id']}: {intent.get('user_question')} (examples: {', '.join(intent.get('sample_user_phrases', []))})"
            )
        lines.extend([
            "Never invent new intents.",
            "Do not generate medical recommendations or diagnoses.",
        ])
        return "\n".join(lines)

    def classify(self, message: str) -> ClassificationResult:
        hard_rule = self._hard_rule_override(message)
        if hard_rule:
            return hard_rule

        if not self.client:
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale="OPENAI_API_KEY not configured"
            )

        system_prompt = self._build_system_prompt()

        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": ClassificationResult.model_json_schema(),
                    "schema_name": "IntentClassification",
                    "strict": True,
                },
            )
        except Exception as exc:  # noqa: BLE001
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale=f"OpenAI call failed: {exc}"
            )

        parsed_text = ""
        try:
            content_blocks = response.output[0].content  # type: ignore[attr-defined]
            if isinstance(content_blocks, list):
                for block in content_blocks:
                    text = getattr(block, "text", None)
                    if text:
                        parsed_text += text
        except Exception:  # noqa: BLE001
            pass

        if not parsed_text and hasattr(response, "output_text"):
            parsed_text = response.output_text  # type: ignore[attr-defined]

        try:
            candidate = ClassificationResult.model_validate(json.loads(parsed_text))
        except (json.JSONDecodeError, ValidationError):
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale="Could not parse model output"
            )

        allowed = set(self.response_bank.get_allowed_intent_ids())
        if candidate.intent_id not in allowed or candidate.confidence < self.confidence_threshold:
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=candidate.confidence,
                slots=candidate.slots,
                rationale="Below confidence threshold or invalid intent"
            )

        return candidate
