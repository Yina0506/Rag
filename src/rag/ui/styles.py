"""Shared CSS + color palette for the Streamlit UI. Kept separate from
app.py so the visual system can be iterated on independently of page logic
— this is the file to touch when the look changes, not the pipeline wiring.
"""

from __future__ import annotations

import streamlit as st

from rag.models import ExistenceStatus, Grade

ACCENT = "#6366f1"
ACCENT_2 = "#a855f7"

GRADE_COLORS: dict[Grade, str] = {
    Grade.SUPPORTS: "#16a34a",
    Grade.WEAK: "#d97706",
    Grade.NEUTRAL: "#64748b",
    Grade.CONTRADICTS: "#dc2626",
    Grade.NOT_FOUND: "#7f1d1d",
}

EXISTENCE_COLORS: dict[ExistenceStatus, str] = {
    ExistenceStatus.EXISTS: "#16a34a",
    ExistenceStatus.NOT_FOUND: "#dc2626",
    ExistenceStatus.RETRACTED: "#d97706",
}

CSS = f"""
<style>
.rag-card {{
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 14px;
    padding: 1.05rem 1.3rem;
    margin-bottom: 0.85rem;
}}

.rag-card-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
}}

.rag-badge {{
    display: inline-block;
    padding: 0.16rem 0.7rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 700;
    color: white;
    letter-spacing: 0.02em;
    white-space: nowrap;
}}

.rag-header {{
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(90deg, {ACCENT}, {ACCENT_2});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.1rem;
}}

.rag-subtle {{
    opacity: 0.65;
    font-size: 0.88rem;
}}

.rag-quote {{
    border-left: 3px solid {ACCENT};
    padding-left: 0.75rem;
    font-style: italic;
    opacity: 0.9;
    margin: 0.5rem 0;
}}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def badge(text: str, color: str) -> str:
    return f'<span class="rag-badge" style="background:{color}">{text}</span>'
