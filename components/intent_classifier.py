from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from typing import Dict, Optional, Tuple

from pathlib import Path

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError

from components.response_bank import ResponseBank

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


class ClassificationResult(BaseModel):
    intent_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    slots: Dict[str, str] = Field(default_factory=dict)
    rationale: str


class IntentClassifier:
    def __init__(self, response_bank: ResponseBank, model: str = "gpt-4.1-mini", confidence_threshold: float = 0.7):
        self._load_env_file()
    def __init__(
        self,
        response_bank: ResponseBank,
        model: str = "gpt-4.1-mini",
        confidence_threshold: float = 0.7,
        client: Optional[OpenAI] = None,
    ):
        load_dotenv()
        self.response_bank = response_bank
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = OpenAI(api_key=self.api_key) if self.api_key else None
        self._last_connectivity_check: Optional[datetime] = None
        self._last_connectivity_ok: Optional[bool] = None
        self._last_connectivity_message: Optional[str] = None

    def _load_env_file(self, path: Path | str = ".env") -> None:
        env_path = Path(path)
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
        self.client: Optional[OpenAI] = client or (OpenAI(api_key=self.api_key) if self.api_key else None)

    def has_api_key(self) -> bool:
        return self.client is not None

    def check_connectivity(self) -> Dict[str, str | bool]:
        if not self.client:
            self._last_connectivity_ok = False
            self._last_connectivity_message = "Missing OPENAI_API_KEY"
            self._last_connectivity_check = datetime.now(timezone.utc)
            return {
                "ok": False,
                "message": self._last_connectivity_message,
                "last_checked": self._last_connectivity_check.isoformat(),
            }

        try:
            self.client.models.list()
            self._last_connectivity_ok = True
            self._last_connectivity_message = "API key loaded and reachable."
        except Exception as exc:  # noqa: BLE001
            self._last_connectivity_ok = False
            self._last_connectivity_message = f"OpenAI connectivity failed: {exc}"

        self._last_connectivity_check = datetime.now(timezone.utc)
        return {
            "ok": bool(self._last_connectivity_ok),
            "message": self._last_connectivity_message or "",
            "last_checked": self._last_connectivity_check.isoformat(),
        }
    def validate_connection(self) -> Tuple[str, str]:
        """Lightweight check to confirm API key presence and connectivity."""

        if not self.api_key:
            return "missing", "Add OPENAI_API_KEY to a local .env file or export it before restarting the app."

        if not self.client:
            return "error", "OpenAI client is unavailable."

        try:
            self.client.models.list()
            return "ok", "API key loaded and reachable."
        except AuthenticationError:
            return "error", "OpenAI rejected the API key. Confirm the OPENAI_API_KEY value and organization access."
        except (APIConnectionError, APITimeoutError):
            return "error", "Unable to reach OpenAI. Check your network/VPN connection and retry."
        except APIStatusError as exc:
            return "error", f"OpenAI validation failed ({exc.status_code}). Try again or reduce request volume."
        except OpenAIError as exc:  # pragma: no cover - defensive fallback
            return "error", f"OpenAI validation failed: {exc}"
        except Exception as exc:  # noqa: BLE001
            return "error", f"Unexpected validation error: {exc}"

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
                rationale="Add an OPENAI_API_KEY to a local .env file or environment variable, then restart the app."
            )

        system_prompt = self._build_system_prompt()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                response_format={"type": "json_object"},
            )
            parsed_text = response.choices[0].message.content or ""
        except TypeError:
            # Some client versions do not support response_format; fall back to plain JSON instructions.
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                        {"role": "system", "content": "Respond with only the JSON object matching the schema."},
                    ],
                )
                parsed_text = response.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                return ClassificationResult(
                    intent_id="__NO_MATCH__",
                    confidence=0.0,
                    slots={},
                    rationale=f"OpenAI call failed: {exc}"
                )
        except Exception as exc:  # noqa: BLE001
        except AuthenticationError:
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale="OpenAI rejected the API key. Double-check OPENAI_API_KEY in your environment or .env file."
            )
        except (APIConnectionError, APITimeoutError):
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale="Unable to reach OpenAI. Check your internet/VPN connection and try again."
            )
        except APIStatusError as exc:
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale=f"OpenAI request failed ({exc.status_code}). Please try again shortly."
            )
        except OpenAIError as exc:
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale=f"OpenAI call failed: {exc}"
            )
        except Exception as exc:  # noqa: BLE001
            return ClassificationResult(
                intent_id="__NO_MATCH__",
                confidence=0.0,
                slots={},
                rationale=f"Unexpected OpenAI error: {exc}"
            )

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
