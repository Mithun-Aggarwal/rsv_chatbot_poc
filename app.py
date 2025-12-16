from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="RSV POC Assistant", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Home")

st.title("RSV Proof of Concept")
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(
        """
        This multi-page Streamlit experience demonstrates a dual-mode chatbot for RSV awareness.
        Use guided mode to browse approved questions, or switch to free text (with an API key) to
        classify your own questions into the response bank. All answers come from structured content
        in the data folder; no medical advice is generated.
        """
    )
    st.info("Keep your OPENAI_API_KEY in the environment to enable free-text classification.")

with col2:
    st.markdown(
        """
        **Highlights**
        - Data-driven response bank (12 intents across 6 categories).
        - Guided and free-text chatbot modes.
        - Deep links into each page for quick navigation.
        - Safe defaults if the API key is missing.
        """
    )

render_chatbot(response_bank, classifier)
