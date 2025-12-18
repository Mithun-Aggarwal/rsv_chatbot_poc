from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="Eligibility", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Eligibility")

st.title("Eligibility Scenarios")

st.markdown(
    """
    Use this page to explore how different audiences—such as older adults or pregnant people—might
    approach RSV vaccination decisions with their clinicians.

    **What you'll find here**
    - High-level reminders that eligibility is determined with a clinician, not the assistant.
    - Separate guidance for older adults and pregnancy-related conversations.
    - Deep links to vaccination timing details so you can continue researching next steps.

    The chatbot stays strictly within the approved response bank and does not make eligibility decisions.
    """
)

render_chatbot(response_bank, classifier, page_path="pages/3_Eligibility.py")
