from __future__ import annotations

from typing import Optional

import streamlit as st

NAV_ITEMS = [
    {"label": "Home", "page": "app.py"},
    {"label": "RSV Basics", "page": "pages/1_RSV_Basics.py"},
    {"label": "Symptoms", "page": "pages/2_Symptoms.py"},
    {"label": "Eligibility", "page": "pages/3_Eligibility.py"},
    {"label": "Vaccination", "page": "pages/4_Vaccination.py"},
    {"label": "Prevention", "page": "pages/5_Prevention.py"},
    {"label": "Appointments", "page": "pages/6_Appointments.py"},
    {"label": "Get Support", "page": "pages/7_Get_Support.py"},
]


def render_top_nav(active_label: Optional[str] = None):
    """Render a simple top navigation bar using Streamlit page links."""
    cols = st.columns(len(NAV_ITEMS))
    for col, item in zip(cols, NAV_ITEMS):
        with col:
            st.page_link(item["page"], label=item["label"], icon="" if item["label"] != active_label else "👉")
