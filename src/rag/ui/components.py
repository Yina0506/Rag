"""Reusable Streamlit render helpers — one function per data-contract type
from `rag.models`, so `app.py` stays focused on layout/flow, not markup.
"""

from __future__ import annotations

import streamlit as st

from rag.models import AuditFinding, Direction, Limitation, LimitationType, Verdict
from rag.ui.styles import GRADE_COLORS, badge


def verdict_card(verdict: Verdict) -> None:
    color = GRADE_COLORS[verdict.grade]
    authors = ", ".join(verdict.paper.authors[:3]) or "Unknown authors"
    year = f" &middot; {verdict.paper.year}" if verdict.paper.year else ""
    retracted = " &middot; ⚠️ RETRACTED" if verdict.paper.retracted else ""
    st.markdown(
        f"""<div class="rag-card">
            <div class="rag-card-row">
                <strong>{verdict.paper.title}</strong>
                {badge(verdict.grade.value, color)}
            </div>
            <div class="rag-subtle">{authors}{year} &middot;
                confidence {verdict.confidence:.0%}{retracted}</div>
            <div class="rag-quote">{verdict.justification}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    if verdict.paper.doi:
        st.caption(f"DOI: [{verdict.paper.doi}](https://doi.org/{verdict.paper.doi})")


def audit_finding_card(finding: AuditFinding) -> None:
    grade_line = ""
    if finding.verdict:
        grade_line = (
            f'<div class="rag-subtle">Grade: {finding.verdict.grade.value} '
            f"({finding.verdict.confidence:.0%})</div>"
        )
    st.markdown(
        f"""<div class="rag-card">
            <div class="rag-card-row">
                <strong>`{finding.citation_key}`</strong>
                <span style="font-size:1.3rem">{finding.symbol}</span>
            </div>
            <div class="rag-quote">{finding.claim_text}</div>
            <div class="rag-subtle">Existence: {finding.existence.value}</div>
            {grade_line}
        </div>""",
        unsafe_allow_html=True,
    )
    if finding.verdict:
        st.caption(finding.verdict.justification)
    if finding.suggested_citation:
        st.info(f"Suggested instead: **{finding.suggested_citation.title}**")


def limitation_card(limitation: Limitation) -> None:
    color = "#6366f1" if limitation.type == LimitationType.STATED else "#a855f7"
    st.markdown(
        f"""<div class="rag-card">
            {badge(limitation.type.value.upper(), color)}
            <div style="margin-top:0.5rem">{limitation.text}</div>
            <div class="rag-subtle">from {limitation.paper_id}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def direction_card(direction: Direction, rank: int) -> None:
    status_color = "#6366f1" if direction.still_open else "#16a34a"
    status_text = "OPEN" if direction.still_open else "ADDRESSED"
    with st.expander(f"#{rank} — {direction.label}  ({direction.frequency} papers)"):
        st.markdown(badge(status_text, status_color), unsafe_allow_html=True)
        if direction.solving_papers:
            st.caption(f"Addressed by: {', '.join(direction.solving_papers)}")
        st.markdown("**Member limitations:**")
        for limitation in direction.member_limitations:
            st.markdown(f"- {limitation.text} — *{limitation.paper_id}*")
