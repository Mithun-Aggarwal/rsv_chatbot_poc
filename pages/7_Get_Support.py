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

st.markdown(
    """
    Find links to supportive resources and understand when to escalate to emergency care.

    **Support resources**
    - Quick reminders to seek local emergency services for severe breathing issues.
    - Links to general support resources that are aligned with the response bank content.
    - Reinforcement that this assistant does not provide triage or medical advice.

    The chatbot's hard-rule overrides immediately route urgent phrases to emergency guidance within the response bank.
    """
)

render_chatbot(response_bank, classifier, page_path="pages/7_Get_Support.py")
