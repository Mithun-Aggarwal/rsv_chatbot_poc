from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import sys
from pathlib import Path

import httpx
import pytest

from openai import APIConnectionError, AuthenticationError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from components.intent_classifier import IntentClassifier  # noqa: E402
from components.response_bank import ResponseBank  # noqa: E402


class DummyModels:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def list(self):  # noqa: D401 - simple stub
        if self.should_fail:
            raise RuntimeError("models list failed")
        return {"data": []}


class FakeResponse:
    def __init__(self, content: str):
        self.choices = [
            type("Choice", (), {"message": type("Msg", (), {"content": content})()})()
        ]


class NoResponseFormatClient:
    def __init__(self, content: str):
        self._content = content
        self.models = DummyModels()
        self.chat = self
        self.completions = self
        self.calls = 0

    def create(self, *_, **kwargs):
        self.calls += 1
        if "response_format" in kwargs and self.calls == 1:
            raise TypeError("response_format not supported")
        return FakeResponse(self._content)


class FailingClient:
    def __init__(self, error: Exception):
        self._error = error
        self.models = DummyModels(should_fail=True)
        self.chat = self
        self.completions = self

    def create(self, *_, **__):
        raise self._error


def test_missing_api_key_returns_no_match(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bank = ResponseBank()
    classifier = IntentClassifier(response_bank=bank)
    classifier.client = None

    result = classifier.classify("hello")

    assert result.intent_id == "__NO_MATCH__"
    assert "OPENAI_API_KEY" in result.rationale


def test_typeerror_response_format_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    bank = ResponseBank()
    payload = {
        "intent_id": bank.intents[0]["intent_id"],
        "confidence": 0.91,
        "slots": {},
        "rationale": "ok",
    }
    client = NoResponseFormatClient(json.dumps(payload))

    classifier = IntentClassifier(response_bank=bank)
    classifier.client = client
    classifier.api_key = "test"

    result = classifier.classify("hello")

    assert result.intent_id == payload["intent_id"]
    assert client.calls >= 2  # attempted response_format then fell back


def test_connectivity_failure_reports_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    bank = ResponseBank()
    client = FailingClient(RuntimeError("boom"))

    classifier = IntentClassifier(response_bank=bank)
    classifier.client = client
    classifier.api_key = "test"

    status = classifier.check_connectivity()

    assert status["ok"] is False
    assert "failed" in status["message"].lower()
class FakeContentBlock:
    def __init__(self, text: str):
        self.text = text


class FakeResponseChunk:
    def __init__(self, text: str):
        self.content = [FakeContentBlock(text)]


class FakeOpenAIResponse:
    def __init__(self, text: str):
        self.output = [FakeResponseChunk(text)]


class FakeResponsesClient:
    def __init__(self, *, exc: Exception | None = None, response_text: str | None = None):
        self.exc = exc
        self.response_text = response_text or '{"intent_id": "eligible", "confidence": 0.9, "slots": {}, "rationale": "match"}'

    def create(self, **_: object) -> FakeOpenAIResponse:
        if self.exc:
            raise self.exc
        return FakeOpenAIResponse(self.response_text)


class FakeModelsClient:
    def __init__(self, *, exc: Exception | None = None):
        self.exc = exc

    def list(self) -> list[str]:
        if self.exc:
            raise self.exc
        return ["ok"]


class FakeOpenAIClient:
    def __init__(self, *, responses_exc: Exception | None = None, models_exc: Exception | None = None, response_text: str | None = None):
        self.responses = FakeResponsesClient(exc=responses_exc, response_text=response_text)
        self.models = FakeModelsClient(exc=models_exc)


def build_response_bank() -> ResponseBank:
    intents = [
        {
            "intent_id": "eligible",
            "user_question": "Am I eligible?",
            "response": "Eligibility details.",
        }
    ]
    return ResponseBank(bank={"intents": intents}, page_map={})


def test_classify_without_key_returns_actionable_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    classifier = IntentClassifier(response_bank=build_response_bank(), client=None)

    result = classifier.classify("Hello")

    assert result.intent_id == "__NO_MATCH__"
    assert "OPENAI_API_KEY" in result.rationale
    assert "env" in result.rationale.lower()


def test_classify_invalid_key_surfaces_authentication_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "bad-key")
    request = httpx.Request("GET", "https://api.openai.com")
    auth_error = AuthenticationError("auth failed", response=httpx.Response(401, request=request), body=None)
    classifier = IntentClassifier(
        response_bank=build_response_bank(),
        client=FakeOpenAIClient(responses_exc=auth_error),
    )

    result = classifier.classify("Hello")

    assert result.intent_id == "__NO_MATCH__"
    assert "rejected the API key" in result.rationale


def test_classify_network_failure_returns_retriable_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "network-key")
    request = httpx.Request("GET", "https://api.openai.com")
    network_error = APIConnectionError(request=request)
    classifier = IntentClassifier(
        response_bank=build_response_bank(),
        client=FakeOpenAIClient(responses_exc=network_error),
    )

    result = classifier.classify("Hello")

    assert result.intent_id == "__NO_MATCH__"
    assert "Unable to reach OpenAI" in result.rationale


def test_classify_success_path_uses_response_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "success-key")
    classifier = IntentClassifier(
        response_bank=build_response_bank(),
        client=FakeOpenAIClient(response_text='{"intent_id": "eligible", "confidence": 0.9, "slots": {}, "rationale": "match"}'),
    )

    result = classifier.classify("Hello")

    assert result.intent_id == "eligible"
    assert result.confidence == 0.9
    assert result.rationale == "match"
