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

st.markdown(
    """
    This page summarizes common RSV symptoms and reminders about when to escalate to emergency care.

    **Symptom snapshot**
    - Typical symptoms include congestion, cough, fever, or sore throat.
    - Infants and older adults can progress more quickly to concerning breathing challenges.
    - The experience never provides triage advice—it reiterates when to seek in-person help.

    **Red flag reminders**
    - Severe breathing trouble, blue lips, or chest pain should trigger emergency evaluation.
    - The guided chatbot on this page opens with symptom guidance and points to escalation content when relevant.
    - Deep links in each response send you to the Support page for urgent resources when appropriate.
    """
)

render_chatbot(response_bank, classifier, page_path="pages/2_Symptoms.py")
