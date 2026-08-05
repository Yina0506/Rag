# 10 — Related Work & How We Differ

Prior work exists — this doc keeps it straight so the thesis positions correctly. The point
is NOT to be first; it's to occupy the specific gap the others leave.

## Existing tools / papers (verify current status before citing in thesis)

**Citation verification / existence:**
- *Citation-Hallucination-Detection* (GitHub, Vikranth3140) — hybrid: exact bib lookup +
  fuzzy match + optional LLM verification over Crossref/OpenAlex/S2. Very close to our
  existence gate + draft audit.
- *CheckIfExist* (arXiv) — real-time bibliographic validation against scholarly DBs.
- *rag-citation* (GitHub, rahulanand1103) — auto-citation for RAG output; NER + semantic sim.

**Citation suggestion:**
- *CitationFinder* (GitHub, hemmokarja) — RAG citation finder for any sentence (our Mode A).
  Note its author's own epistemic caveat: research should build args from literature, not
  find literature to fit arbitrary claims — engage with this directly.
- *Context-aware citation suggestion* (ScienceDirect, 2026) — retrieval-centric; reports
  naive LLM prompting <10% citation accuracy. Use as the baseline result we reproduce.

**Scientific QA with citations:**
- *PaperQA2* (GitHub, Future-House) — mature agentic RAG over scientific PDFs, metadata-aware,
  includes retraction check + contradiction detection. The heavyweight; benchmark against it.

**Limitations / directions:**
- *AI-Research-Analyzer* (GitHub, iDharshan) — RAG that flags gaps/limitations, but
  **single-paper**, no cross-field aggregation.
- *BAGELS* (arXiv 2505.18207) — benchmarks automated limitation extraction; key findings we
  build on: limitations are underreported, and implicit ones surface via similar/later papers.
  Their OpenReview-comment ground truth is reusable for our Phase-5 eval.

## Our differentiators (the thesis pitch)

1. **Graded, passage-level entailment** for "does this paper support THIS claim" — most
   tools stop at existence or relevance, not rigorous graded support.
2. **Willingness to abstain** (NOT_FOUND) as a first-class, tested behavior.
3. **Cross-field limitation aggregation → clustered directions** — beyond single-paper gap
   flagging; frequency-weighted directions across a whole field.
4. **Openness detection** — using the citation graph + entailment to tell *still-open* gaps
   from already-solved ones. This is the least-explored piece and the strongest novelty.
5. **Unified backbone** — one retrieval+entailment core serving verification AND discovery,
   with the citation graph reused across both.

## Action for the writing phase

- Re-run a literature check right before submission (this field moves fast).
- Frame contribution as (3)+(4), with (1)+(2) as solid engineering, not novelty claims.
