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

st.markdown(
    """
    Learn how RSV impacts communities and why this proof of concept focuses on navigation and education.

    **Key takeaways**
    - RSV is a common respiratory virus with seasonal surges that disproportionately affect infants and older adults.
    - This site does not diagnose conditions; it curates approved educational responses and links you to other sections.
    - Guided mode automatically surfaces the most relevant question for this page so you can move quickly.
    - Free-text mode requires an API key and only classifies to the approved intents.

    **How this prototype is structured**
    - A response bank keeps answers consistent across pages.
    - The assistant highlights deep links so you can hop between navigation topics without searching.
    - Next-best suggestions show related questions once you review the primary guidance.
    """
)

render_chatbot(response_bank, classifier, page_path="pages/1_RSV_Basics.py")
