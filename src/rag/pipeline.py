"""The entrypoints the UI (and CLI/tests) call. Keep this the single place that
wires retrieval -> existence gate -> entailment together, per module.

Implement incrementally, one phase at a time (docs/03..08):
- verify_claim          Phase 1 (retrieval-only) -> Phase 2 (+ gate) -> Phase 3 (+ entailment, done)
- audit_draft           Phase 4 (done)
- extract_limitations   Phase 5 (done)
- discover_directions   Phase 6 (done)
"""

from __future__ import annotations

from rag.models import Candidate, Claim, Direction, ExistenceStatus, Grade, Limitation, Verdict

_GRADE_RANK = {
    Grade.CONTRADICTS: 0,
    Grade.NOT_FOUND: 0,
    Grade.NEUTRAL: 1,
    Grade.WEAK: 2,
    Grade.SUPPORTS: 3,
}


def retrieve_candidates(claim: str, k: int = 5) -> list[Candidate]:
    """API search -> embed/index -> vector search -> rerank -> existence gate
    -> top-k Candidates. The existence gate (docs/04-phase-2) is applied here,
    not by callers — this is the single choke point nothing bypasses before
    presentation, per docs/CONVENTIONS.md."""
    from rag.retrieval.embed import embed_text
    from rag.retrieval.index import search, upsert_papers
    from rag.retrieval.rerank import rerank
    from rag.retrieval.sources import search_papers

    papers = search_papers(claim, limit=max(k * 4, 20))
    # Live-caught bug: a paper with no abstract has no evidence text for
    # rerank/entailment to reason over. rerank.py's fallback to bare title
    # then lets a title-only textual match (e.g. "X Attention Is All You
    # Need" against the claim "attention is all you need") outscore a real,
    # topically-relevant paper whose abstract doesn't literally repeat the
    # query phrase — and downstream entailment can only produce an
    # uninformative NEUTRAL/empty-justification verdict from empty evidence
    # anyway. Filtering here (not just in rerank) keeps abstract-less papers
    # out of the whole candidate pool, per "only reason over retrieved text."
    papers = [p for p in papers if p.abstract]
    if not papers:
        return []
    upsert_papers(papers)

    query_vector = embed_text(claim)
    candidates = search(query_vector, k=max(k * 2, 10))
    reranked = rerank(claim, candidates)
    return _apply_existence_gate(reranked)[:k]


def _apply_existence_gate(candidates: list[Candidate]) -> list[Candidate]:
    """Drop candidates that don't resolve to a real paper; flag (not drop)
    retracted ones so callers can still surface a "cite something else"
    signal instead of the paper silently vanishing."""
    from rag.verify.existence import existence_verdict

    kept = []
    for candidate in candidates:
        verdict = existence_verdict(candidate.paper)
        if verdict == ExistenceStatus.NOT_FOUND:
            continue
        if verdict == ExistenceStatus.RETRACTED:
            candidate = candidate.model_copy(
                update={"paper": candidate.paper.model_copy(update={"retracted": True})}
            )
        kept.append(candidate)
    return kept


def verify_claim(claim: str, k: int = 5) -> list[Verdict]:
    """retrieve -> existence gate -> entail -> sort -> graded Verdicts.

    Returns `[]` only when retrieval/the existence gate found nothing at all
    (nothing to build a Verdict from — Verdict.paper is required). When real
    candidates exist but none clear WEAK, the top Verdict's grade is
    overridden to NOT_FOUND rather than silently ranking a bad candidate
    first — docs/05-phase-3-entailment.md's "the tool must be willing to say
    no supporting paper found" is enforced here, not left to the caller.
    """
    from rag.verify.entailment import _run_entailer

    candidates = retrieve_candidates(claim, k=k)
    if not candidates:
        return []

    claim_obj = Claim(text=claim)
    verdicts = []
    for candidate in candidates:
        evidence = candidate.paper.abstract or ""
        grade, confidence, justification = _run_entailer(claim, evidence)
        verdicts.append(
            Verdict(
                claim=claim_obj,
                paper=candidate.paper,
                grade=grade,
                evidence_passage=evidence,
                confidence=confidence,
                justification=justification,
            )
        )
    verdicts.sort(key=lambda v: _GRADE_RANK[v.grade], reverse=True)

    if _GRADE_RANK[verdicts[0].grade] < _GRADE_RANK[Grade.WEAK]:
        best = verdicts[0]
        verdicts[0] = best.model_copy(
            update={
                "grade": Grade.NOT_FOUND,
                "justification": (
                    f"No candidate paper supports this claim (closest candidate graded "
                    f"{best.grade.value}, confidence {best.confidence:.2f})."
                ),
            }
        )
    return verdicts


def audit_draft(path: str, bib_path: str | None = None) -> dict:
    """Ingest a draft (.tex/.bib, or PDF via GROBID) and audit every (claim,
    citation) pair — see `audit.draft.audit` for the full flow and the
    ✅/⚠️/❌/🚫 symbol mapping."""
    from rag.audit.draft import audit

    return audit(path, bib_path=bib_path)


def extract_limitations(paper_id: str) -> list[Limitation]:
    """Resolve a paper by id, fetch full text if an OA PDF can be found
    (falls back to abstract-only otherwise — `extract_stated` just finds
    fewer/no sections, which correctly triggers the implicit path), and
    extract stated + implicit limitations."""
    from rag.limitations.extract import extract_limitations as _extract
    from rag.retrieval.fulltext import fetch_full_text
    from rag.retrieval.sources import get_paper

    paper = get_paper(paper_id)
    if paper is None:
        return []

    sections = fetch_full_text(paper)
    full_text = (
        "\n".join(f"{heading}\n{text}" for heading, text in sections.items())
        if sections
        else (paper.abstract or "")
    )
    return _extract(paper, full_text)


def discover_directions(field_query: str, corpus_size: int = 20) -> list[Direction]:
    """Corpus build -> extract (per paper, Phase 5) -> cluster -> openness ->
    ranked Directions. `corpus_size` is deliberately small by default — each
    paper can trigger several similar-paper searches and LLM entailment
    calls in Phase 5's implicit-extraction path, so this is expensive to run
    at real field-corpus scale (hundreds-2000 papers, per docs/02-data-sources.md);
    the bounded-corpus-with-cutoff-year building described there isn't
    implemented as its own step yet — this just searches `field_query`
    directly. Revisit if/when running this at real scale."""
    from rag.directions.cluster import build_directions
    from rag.directions.openness import check_openness
    from rag.limitations.extract import extract_limitations as _extract_limitations
    from rag.retrieval.sources import search_papers

    corpus = search_papers(field_query, limit=corpus_size)

    all_limitations: list[Limitation] = []
    for paper in corpus:
        all_limitations.extend(_extract_limitations(paper, paper.abstract or ""))

    directions = build_directions(all_limitations)
    return [check_openness(direction) for direction in directions]
