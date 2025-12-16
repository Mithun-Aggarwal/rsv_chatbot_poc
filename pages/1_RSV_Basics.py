from __future__ import annotations

import streamlit as st

from components.chatbot_widget import render_chatbot
from components.intent_classifier import IntentClassifier
from components.navigation import render_top_nav
from components.response_bank import ResponseBank

st.set_page_config(page_title="RSV Basics", layout="wide")

response_bank = ResponseBank()
classifier = IntentClassifier(response_bank=response_bank)

render_top_nav(active_label="RSV Basics")

st.title("RSV Basics")

st.write(
    """
    Learn how RSV impacts communities and why this proof of concept focuses on navigation and education.
    Key takeaways include:
    - RSV is a common respiratory virus with seasonal surges.
    - This site does not diagnose conditions; it curates approved educational responses.
    - Free-text mode requires an API key and only classifies to the approved intents.
    """
)

render_chatbot(response_bank, classifier)
