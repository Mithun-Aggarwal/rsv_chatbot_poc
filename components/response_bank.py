from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_BANK_PATH = DATA_DIR / "response_bank.json"
DEFAULT_PAGE_MAP_PATH = DATA_DIR / "intent_to_page_map.json"


@lru_cache(maxsize=1)
def load_response_bank(path: Path = DEFAULT_BANK_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_intent_to_page_map(path: Path = DEFAULT_PAGE_MAP_PATH) -> Dict[str, List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class ResponseBank:
    """Helper for working with the response bank and related mappings."""

    def __init__(self, bank: Optional[Dict[str, Any]] = None, page_map: Optional[Dict[str, List[Dict[str, str]]]] = None):
        self.bank = bank or load_response_bank()
        self.page_map = page_map or load_intent_to_page_map()
        self.intents = self.bank.get("intents", [])
        self.intent_lookup = {intent["intent_id"]: intent for intent in self.intents}

    def get_categories(self) -> List[str]:
        seen = []
        for intent in self.intents:
            category = intent.get("category", "Other")
            if category not in seen:
                seen.append(category)
        return seen

    def get_intents_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [intent for intent in self.intents if intent.get("category") == category]

    def get_intent_by_id(self, intent_id: str) -> Optional[Dict[str, Any]]:
        return self.intent_lookup.get(intent_id)

    def get_allowed_intent_ids(self) -> List[str]:
        return list(self.intent_lookup.keys())

    def get_next_best(self, intent_id: str) -> List[Dict[str, Any]]:
        intent = self.get_intent_by_id(intent_id)
        if not intent:
            return []
        return [self.intent_lookup[i] for i in intent.get("next_best_intent_ids", []) if i in self.intent_lookup]

    def get_page_links_for_intent(self, intent_id: str) -> List[Dict[str, str]]:
        return self.page_map.get(intent_id, [])

    def get_training_phrases(self) -> List[str]:
        phrases: List[str] = []
        for intent in self.intents:
            for phrase in intent.get("sample_user_phrases", []):
                phrases.append(phrase)
        return phrases
