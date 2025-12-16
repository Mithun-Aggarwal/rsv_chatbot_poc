from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="Support", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="Get Support")

st.title("Support and Escalation")

st.write(
    """
    Find links to supportive resources and understand when to escalate to emergency care. The chatbot's
    hard-rule overrides immediately route urgent phrases to emergency guidance within the response bank.
    """
)

render_chatbot(response_bank, classifier)
