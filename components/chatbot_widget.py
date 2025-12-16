from __future__ import annotations

from typing import Dict, List

import streamlit as st

from components.intent_classifier import IntentClassifier
from components.response_bank import ResponseBank

FALLBACK_RESPONSE = "I could not find a matching topic in the response bank. Try a guided question or rephrase."


def _init_state():
    st.session_state.setdefault("chat_mode", "Guided")
    st.session_state.setdefault("guided_category", None)
    st.session_state.setdefault("guided_history", [])
    st.session_state.setdefault("free_history", [])
    st.session_state.setdefault("last_intent_id", None)


def _render_history(history_key: str):
    for message in st.session_state.get(history_key, []):
        with st.chat_message(message.get("role", "assistant")):
            st.write(message.get("content", ""))
            intent_id = message.get("intent_id")
            if intent_id and message.get("role") == "assistant":
                _render_deep_links(intent_id)


def _append_history(history_key: str, role: str, content: str, intent_id: str | None = None):
    st.session_state[history_key].append({"role": role, "content": content, "intent_id": intent_id})


def _render_deep_links(intent_id: str):
    bank = st.session_state.get("response_bank")
    if not isinstance(bank, ResponseBank):
        return
    links = bank.get_page_links_for_intent(intent_id)
    if not links:
        return
    cols = st.columns(len(links))
    for col, link in zip(cols, links):
        with col:
            st.page_link(link["page"], label=f"Go to {link['label']}", icon="➡️")


def _render_next_best(next_best: List[Dict], response_bank: ResponseBank, history_key: str):
    if not next_best:
        return
    st.caption("Next best questions")
    cols = st.columns(len(next_best))
    for col, intent in zip(cols, next_best):
        with col:
            if st.button(intent.get("user_question", intent.get("display_name", "More")), key=f"nbq-{intent['intent_id']}"):
                _handle_intent(intent, history_key, response_bank)
                st.session_state["last_intent_id"] = intent["intent_id"]


def render_chatbot(response_bank: ResponseBank, classifier: IntentClassifier):
    """Render chatbot widget with guided and free-text modes."""

    _init_state()
    st.session_state["response_bank"] = response_bank

    st.divider()
    st.subheader("RSV Assistant")

    mode_disabled = not classifier.has_api_key()
    mode = st.radio(
        "Choose a mode",
        ["Guided", "Free text"],
        horizontal=True,
        index=0 if st.session_state.get("chat_mode") == "Guided" or mode_disabled else 1,
        disabled=False,
    )
    st.session_state["chat_mode"] = mode if not (mode == "Free text" and mode_disabled) else "Guided"

    if mode_disabled:
        st.info("Free-text mode is disabled because OPENAI_API_KEY is not set. Guided questions remain available.")

    if st.session_state["chat_mode"] == "Guided":
        _render_guided(response_bank)
    else:
        _render_free_text(response_bank, classifier)


def _render_guided(response_bank: ResponseBank):
    categories = response_bank.get_categories()
    if categories and st.session_state.get("guided_category") is None:
        st.session_state["guided_category"] = categories[0]

    st.selectbox(
        "Choose a topic",
        categories,
        key="guided_category",
        help="Questions are generated from the response bank."
    )

    selected_category = st.session_state.get("guided_category")
    intents = response_bank.get_intents_by_category(selected_category)

    st.write("Select a question:")
    cols = st.columns(2)
    for idx, intent in enumerate(intents):
        col = cols[idx % 2]
        with col:
            if st.button(intent.get("user_question", intent.get("display_name")), key=f"guided-{intent['intent_id']}"):
                _handle_intent(intent, "guided_history", response_bank)
                st.session_state["last_intent_id"] = intent["intent_id"]

    st.markdown("---")
    st.caption("Conversation")
    _render_history("guided_history")

    if st.session_state.get("last_intent_id"):
        next_best = response_bank.get_next_best(st.session_state["last_intent_id"])
        _render_next_best(next_best, response_bank, "guided_history")


def _handle_intent(intent: Dict, history_key: str, response_bank: ResponseBank):
    question = intent.get("user_question", intent.get("display_name", "Question"))
    _append_history(history_key, "user", question)
    answer = intent.get("response", FALLBACK_RESPONSE)
    _append_history(history_key, "assistant", answer, intent_id=intent.get("intent_id"))


def _render_free_text(response_bank: ResponseBank, classifier: IntentClassifier):
    st.caption("Type your own question. We classify it to an approved intent and respond only from the response bank.")
    user_input = st.text_input("Your question", placeholder="Ask about RSV eligibility, timing, or logistics")
    if st.button("Send", disabled=not classifier.has_api_key() or not user_input.strip()):
        _append_history("free_history", "user", user_input.strip())
        result = classifier.classify(user_input.strip())
        answer_intent = response_bank.get_intent_by_id(result.intent_id)
        if not answer_intent:
            content = FALLBACK_RESPONSE
        else:
            content = answer_intent.get("response", FALLBACK_RESPONSE)
        _append_history("free_history", "assistant", content, intent_id=result.intent_id if answer_intent else None)
        st.session_state["last_intent_id"] = result.intent_id if answer_intent else None

    st.markdown("---")
    st.caption("Conversation")
    _render_history("free_history")

    if st.session_state.get("last_intent_id"):
        next_best = response_bank.get_next_best(st.session_state["last_intent_id"])
        _render_next_best(next_best, response_bank, "free_history")
