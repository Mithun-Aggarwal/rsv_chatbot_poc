from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="Vaccination", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Vaccination")

st.title("Vaccination Details")

st.write(
    """
    Explore high-level vaccination details, such as timing considerations and available products. All
    answers shown here originate from the approved response bank and avoid personal medical guidance.
    """
)

render_chatbot(response_bank, classifier)
