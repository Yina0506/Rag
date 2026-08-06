"""Streamlit UI — a thin presentation layer over `rag.pipeline`. The
pipeline is the thesis, not this file (docs/01-architecture.md's "pipeline
is the thesis, not the UI"): every tab below is "call a pipeline function,
render the result," no business logic lives here.

Run with `make ui` or `uv run streamlit run src/rag/ui/app.py`.
"""

from __future__ import annotations

import os
import tempfile

import streamlit as st

from rag import pipeline
from rag.models import AuditFinding, Grade
from rag.ui.components import audit_finding_card, direction_card, limitation_card, verdict_card
from rag.ui.styles import inject

st.set_page_config(
    page_title="RAG — Citation Verification & Direction Discovery",
    page_icon="📚",
    layout="wide",
)
inject()

st.markdown('<div class="rag-header">RAG</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rag-subtle">Academic citation verification &amp; research-direction '
    "discovery — every result is grounded in retrieved, existence-checked, "
    "entailment-graded evidence. Never from an LLM's memory.</div>",
    unsafe_allow_html=True,
)
st.write("")

for key in ("verify_result", "audit_result", "limitations_result", "directions_result"):
    st.session_state.setdefault(key, None)

tab_verify, tab_audit, tab_limitations, tab_directions = st.tabs(
    ["🔍 Verify a Claim", "📄 Audit a Draft", "🧩 Limitations", "🧭 Directions"]
)

with tab_verify:
    st.subheader("Verify a claim against real literature")
    claim = st.text_area(
        "Claim",
        placeholder="e.g. Transformers rely on attention instead of recurrence.",
        height=100,
    )
    k = st.slider("Candidates to consider", 1, 10, 5)
    st.caption(
        "First call after Ollama's been idle a few minutes can take ~2-3 min "
        "(cold model load) — see docs/PROGRESS.md."
    )
    if st.button("Verify", type="primary", key="verify_btn") and claim.strip():
        try:
            with st.spinner("Retrieving, checking existence, grading entailment…"):
                st.session_state.verify_result = pipeline.verify_claim(claim, k=k)
        except Exception as exc:  # live external calls: surface, don't crash the app
            st.error(f"Verification failed: {exc}")
            st.session_state.verify_result = None

    verdicts = st.session_state.verify_result
    if verdicts is not None:
        if not verdicts:
            st.warning("No candidate papers found at all.")
        else:
            if verdicts[0].grade == Grade.NOT_FOUND:
                st.error("No supporting paper found — the tool is refusing to guess.")
            for verdict in verdicts:
                verdict_card(verdict)

with tab_audit:
    st.subheader("Audit a draft's citations")
    st.caption(
        r"Upload a .tex file (its companion .bib — via \bibliography{} or same "
        "filename — should be uploaded alongside it), or a standalone .bib for an "
        "existence-only sweep."
    )
    tex_file = st.file_uploader("Draft", type=["tex", "bib"], key="audit_main_file")
    bib_file = st.file_uploader(
        "Bibliography (.bib) — only needed if not same-named / not auto-found",
        type=["bib"],
        key="audit_bib_file",
    )
    if st.button("Audit", type="primary", key="audit_btn") and tex_file:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                main_path = os.path.join(tmp_dir, tex_file.name)
                with open(main_path, "wb") as f:
                    f.write(tex_file.getvalue())
                bib_path = None
                if bib_file:
                    bib_path = os.path.join(tmp_dir, bib_file.name)
                    with open(bib_path, "wb") as f:
                        f.write(bib_file.getvalue())
                with st.spinner("Parsing and auditing every citation…"):
                    st.session_state.audit_result = pipeline.audit_draft(
                        main_path, bib_path=bib_path
                    )
        except Exception as exc:
            st.error(f"Audit failed: {exc}")
            st.session_state.audit_result = None

    result = st.session_state.audit_result
    if result is not None:
        summary = result["summary"]
        if summary:
            cols = st.columns(len(summary))
            for col, (symbol, count) in zip(cols, summary.items(), strict=True):
                col.metric(symbol, count)
        else:
            st.info("No citations found in this draft.")
        for finding_dict in result["findings"]:
            audit_finding_card(AuditFinding.model_validate(finding_dict))

with tab_limitations:
    st.subheader("Extract limitations from a paper")
    paper_id = st.text_input(
        "Semantic Scholar paper ID",
        placeholder="e.g. 204e3073870fae3d05bcbc2f6a8e263d9b72e776",
    )
    if st.button("Extract", type="primary", key="extract_btn") and paper_id.strip():
        try:
            with st.spinner("Fetching paper, extracting stated + implicit limitations…"):
                st.session_state.limitations_result = pipeline.extract_limitations(
                    paper_id.strip()
                )
        except Exception as exc:
            st.error(f"Extraction failed: {exc}")
            st.session_state.limitations_result = None

    limitations = st.session_state.limitations_result
    if limitations is not None:
        if not limitations:
            st.info("No limitations found (or the paper id couldn't be resolved).")
        for limitation in limitations:
            limitation_card(limitation)

with tab_directions:
    st.subheader("Discover open research directions in a field")
    field_query = st.text_input(
        "Field / topic", placeholder="e.g. neural Chinese poetry generation evaluation"
    )
    corpus_size = st.slider("Corpus size (papers)", 5, 50, 20)
    st.caption(
        "Expensive: each paper can trigger several searches + LLM calls. A run of "
        "20 papers can take a while — see docs/08-phase-6-direction-discovery.md."
    )
    if st.button("Discover", type="primary", key="discover_btn") and field_query.strip():
        try:
            with st.spinner("Building corpus, extracting, clustering, checking openness…"):
                st.session_state.directions_result = pipeline.discover_directions(
                    field_query.strip(), corpus_size=corpus_size
                )
        except Exception as exc:
            st.error(f"Discovery failed: {exc}")
            st.session_state.directions_result = None

    directions = st.session_state.directions_result
    if directions is not None:
        if not directions:
            st.info("No directions surfaced — try a broader field query or a larger corpus.")
        for i, direction in enumerate(directions, 1):
            direction_card(direction, i)
