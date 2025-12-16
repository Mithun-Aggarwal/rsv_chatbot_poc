from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="Symptoms", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Symptoms")

st.title("Symptoms and Red Flags")

st.write(
    """
    This page summarizes common RSV symptoms and reminders about when to escalate to emergency care.
    The chatbot responses stay within approved messaging and will direct you to seek local emergency
    services for urgent concerns.
    """
)

render_chatbot(response_bank, classifier)
