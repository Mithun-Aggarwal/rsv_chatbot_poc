from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from urllib.parse import urlencode

import streamlit as st

from components.intent_classifier import IntentClassifier
from components.response_bank import ResponseBank

FALLBACK_RESPONSE = "I could not find a matching topic in the response bank. Try a guided question or rephrase."


def _init_state():
    st.session_state.setdefault("chat_mode", "Guided")
    st.session_state.setdefault("guided_history", [])
    st.session_state.setdefault("free_history", [])
    st.session_state.setdefault("last_intent_id", None)
    st.session_state.setdefault("guided_auto_prompts", {})
    st.session_state.setdefault("chat_panel_open", False)
    st.session_state.setdefault("api_status", {"state": "unknown", "message": "Status not checked yet."})
    st.session_state.setdefault("api_status_checked_at", None)
    st.session_state.setdefault("last_mode", st.session_state.get("chat_mode", "Guided"))


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


def _sync_mode_with_query_params():
    requested_mode = st.query_params.get("chat", [None])
    requested_mode = requested_mode[-1] if isinstance(requested_mode, list) else requested_mode
    if not requested_mode:
        return
    normalized = requested_mode.lower()
    if normalized in {"guided", "guide"}:
        st.session_state["chat_mode"] = "Guided"
        st.session_state["chat_panel_open"] = True
    elif normalized in {"free", "free-text", "unguided"}:
        st.session_state["chat_mode"] = "Free text"
        st.session_state["chat_panel_open"] = True
    elif normalized in {"open", "panel"}:
        st.session_state["chat_panel_open"] = True


def _build_mode_link(mode: str) -> str:
    params = dict(st.query_params)
    params.update({"chat": mode, "panel": "open"})
    return f"?{urlencode(params, doseq=True)}"


def _render_mode_launchers():
    guided_link = _build_mode_link("guided")
    free_link = _build_mode_link("free")
    st.markdown(
        f"""
        <style>
        .chat-fab {{
            position: fixed;
            bottom: 1.5rem;
            padding: 0.75rem 1rem;
            border-radius: 999px;
            color: white;
            text-decoration: none;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
            z-index: 9999;
        }}
        .chat-fab:hover {{
            filter: brightness(1.05);
        }}
        .chat-fab.guided {{
            left: 1.25rem;
            background: linear-gradient(135deg, #1a5276, #2471a3);
        }}
        .chat-fab.free {{
            right: 1.25rem;
            background: linear-gradient(135deg, #117a65, #16a085);
        }}
        @media (max-width: 640px) {{
            .chat-fab {{
                bottom: 0.75rem;
                font-size: 0.9rem;
            }}
            .chat-fab.guided {{ left: 0.75rem; right: auto; }}
            .chat-fab.free {{ right: 0.75rem; left: auto; }}
        }}
        @media (max-width: 420px) {{
            .chat-fab {{
                padding: 0.65rem 0.85rem;
                font-size: 0.85rem;
            }}
        }}
        </style>
        <a class="chat-fab guided" href="{guided_link}" aria-label="Open guided chat panel" title="Open guided chatbot panel">🧭 Guided chat</a>
        <a class="chat-fab free" href="{free_link}" aria-label="Open free-text chat panel" title="Open free-text chatbot panel">✨ Free-text chat</a>
        """,
        unsafe_allow_html=True,
    )


def render_chatbot(response_bank: ResponseBank, classifier: IntentClassifier, page_path: str | None = None):
    """Render chatbot entrypoints with a reusable floating panel that supports both modes."""

    _init_state()
    _update_api_status(classifier)
    _sync_mode_with_query_params()
    st.session_state["response_bank"] = response_bank

    _render_mode_launchers()

    _sync_panel_visibility()
    _render_panel_shell(response_bank, classifier, page_path)


def _sync_panel_visibility():
    panel_param = st.query_params.get("panel", [None])
    panel_param = panel_param[-1] if isinstance(panel_param, list) else panel_param
    if panel_param:
        st.session_state["chat_panel_open"] = panel_param.lower() == "open"


def _render_panel_shell(response_bank: ResponseBank, classifier: IntentClassifier, page_path: str | None):
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {{
            width: min(420px, 90vw) !important;
        }}
        section[data-testid="stSidebar"] .block-container {{
            padding: 1rem;
            gap: 0.75rem;
        }}
        section[data-testid="stSidebar"] h2 {{
            margin-bottom: 0;
        }}
        section[data-testid="stSidebar"] .mode-toggle .stRadio [role="radiogroup"] {{
            width: 100%;
        }}
        section[data-testid="stSidebar"] .mode-toggle label {{
            font-weight: 600;
        }}
        @media (max-width: 640px) {{
            section[data-testid="stSidebar"] {{
                width: min(100vw, 380px) !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.get("chat_panel_open"):
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] { display: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        return

    with st.sidebar:
        header_cols = st.columns([1, 1])
        with header_cols[0]:
            st.markdown("### RSV Assistant", help="Guided and free-text responses with deep links.")
        with header_cols[1]:
            if st.button("Close panel", key="close-chat-panel", help="Collapse the chat panel", use_container_width=True):
                st.session_state["chat_panel_open"] = False
                st.query_params["panel"] = "closed"
                return

        _render_api_status(classifier)

        mode_disabled = not classifier.has_api_key()
        previous_mode = st.session_state.get("last_mode", st.session_state.get("chat_mode", "Guided"))
        st.caption("Switch modes while keeping your conversation history intact.")
        mode = st.radio(
            "Choose a mode",
            ["Guided", "Free text"],
            horizontal=True,
            index=0 if st.session_state.get("chat_mode") == "Guided" or mode_disabled else 1,
            disabled=False,
            label_visibility="visible",
            key="chat-panel-mode",
        )
        st.session_state["chat_mode"] = mode if not (mode == "Free text" and mode_disabled) else "Guided"
        mode_changed = previous_mode != st.session_state["chat_mode"]
        st.session_state["last_mode"] = st.session_state["chat_mode"]

        if st.session_state["chat_mode"] == "Free text" and mode_changed:
            _update_api_status(classifier, force=True)

        if mode_disabled:
            st.info("Free-text mode is disabled because OPENAI_API_KEY is not set. Guided questions remain available.")

        if st.session_state["chat_mode"] == "Guided":
            _render_guided(response_bank, page_path)
        else:
            _render_free_text(response_bank, classifier)


def _render_guided(response_bank: ResponseBank, page_path: str | None):
    page_intent = response_bank.get_primary_intent_for_page(page_path) or (response_bank.intents[0] if response_bank.intents else None)

    if page_intent:
        st.success(
            f"Guided mode is anchored to this page. Showing the recommended question: **{page_intent.get('user_question', page_intent.get('display_name', 'Question'))}**"
        )

        page_key = page_path or "__root__"
        seen_map: Dict[str, str] = st.session_state.get("guided_auto_prompts", {})
        already_present = any(
            msg.get("intent_id") == page_intent["intent_id"] and msg.get("role") == "assistant"
            for msg in st.session_state.get("guided_history", [])
        )
        if seen_map.get(page_key) != page_intent["intent_id"] and not already_present:
            _handle_intent(page_intent, "guided_history", response_bank)
            st.session_state["last_intent_id"] = page_intent["intent_id"]
            st.session_state["guided_auto_prompts"][page_key] = page_intent["intent_id"]
    else:
        st.info("No page-specific guided prompt found. Guided mode will activate once intents are available.")

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
    if not classifier.has_api_key():
        st.info("Add your OPENAI_API_KEY to a local .env file (see .env.example) and restart to enable free text.")
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

        if not classifier.has_api_key():
            st.warning("Free text requests need an OpenAI API key. Add it to a local .env file and restart the app.")
        elif result.intent_id == "__NO_MATCH__":
            st.warning("The classifier could not match your question with enough confidence. Try rephrasing or use guided mode.")

    st.markdown("---")
    st.caption("Conversation")
    _render_history("free_history")

    if st.session_state.get("last_intent_id"):
        next_best = response_bank.get_next_best(st.session_state["last_intent_id"])
        _render_next_best(next_best, response_bank, "free_history")


def _render_api_status(classifier: IntentClassifier):
    status = st.session_state.get("api_status", {})
    checked_at = st.session_state.get("api_status_checked_at")
    state = status.get("state", "unknown")
    message = status.get("message", "")

    badges = {
        "ok": {"label": "API key loaded", "color": "#16a085", "emoji": "✅"},
        "missing": {"label": "Missing key", "color": "#b03a2e", "emoji": "⚠️"},
        "error": {"label": "Connection error", "color": "#d35400", "emoji": "❌"},
        "unknown": {"label": "Not checked", "color": "#7f8c8d", "emoji": "ℹ️"},
    }

    badge = badges.get(state, badges["unknown"])
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown(
            f"""
            <div style="padding: 0.75rem 0.85rem; border-radius: 0.75rem; background: rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.05);">
                <div style="display: flex; align-items: center; gap: 0.35rem; margin-bottom: 0.15rem;">
                    <span style="font-size: 1rem;">{badge['emoji']}</span>
                    <span style="background:{badge['color']}; color: white; padding: 0.2rem 0.55rem; border-radius: 999px; font-weight: 700; font-size: 0.85rem;">{badge['label']}</span>
                </div>
                <div style="font-size: 0.9rem; color: #2c3e50;">{message}</div>
                <div style="font-size: 0.8rem; color: #7f8c8d;">{('Last checked ' + checked_at) if checked_at else 'Check status to confirm connectivity.'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[1]:
        if st.button("Re-check", key="recheck-api-status", help="Validate the API key and connectivity", use_container_width=True):
            _update_api_status(classifier, force=True)


def _update_api_status(classifier: IntentClassifier, *, force: bool = False):
    status = st.session_state.get("api_status", {"state": "unknown", "message": "Status not checked yet."})
    if not force and status.get("state") in {"ok", "missing", "error"}:
        return status

    with st.spinner("Checking OpenAI connectivity..."):
        state, message = classifier.validate_connection()

    st.session_state["api_status"] = {"state": state, "message": message}
    st.session_state["api_status_checked_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return st.session_state["api_status"]
