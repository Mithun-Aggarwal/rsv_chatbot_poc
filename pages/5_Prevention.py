from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="Prevention", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Prevention")

st.title("Prevention and Preparedness")

st.markdown(
    """
    Simple prevention steps such as hand hygiene and masking can reduce RSV spread.

    **Prevention guidance covered**
    - Everyday tactics: handwashing, staying home when sick, and cleaning shared surfaces.
    - Community reminders: masking during surges and protecting high-risk loved ones.
    - When prevention is not enough: links to symptom and support pages for escalation.

    Use the chatbot to quickly surface approved prevention tips and navigate to other sections with deep links.
    """
)

render_chatbot(response_bank, classifier, page_path="pages/5_Prevention.py")
