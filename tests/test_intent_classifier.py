from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
