from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="Appointments", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Appointments")

st.title("Scheduling and Coverage")

st.write(
    """
    Discover scheduling reminders and coverage considerations for RSV visits. The chatbot leverages the
    response bank to share consistent information and deep-link you to other relevant pages.
    """
)

render_chatbot(response_bank, classifier)
