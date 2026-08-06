"""The entrypoints the UI (and CLI/tests) call. Keep this the single place that
wires retrieval -> existence gate -> entailment together, per module.

Implement incrementally, one phase at a time (docs/03..08):
- verify_claim          Phase 1 (retrieval-only) -> Phase 2 (+ gate) -> Phase 3 (+ entailment, done)
- audit_draft           Phase 4
- extract_limitations   Phase 5
- discover_directions   Phase 6
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


def audit_draft(path: str) -> dict:
    """Phase 4: ingest a draft (PDF/.bib/.tex), audit every (claim, citation) pair."""
    raise NotImplementedError("Phase 4: audit/draft.py")


def extract_limitations(paper_id: str) -> list[Limitation]:
    """Phase 5: stated + implicit limitations for one paper."""
    raise NotImplementedError("Phase 5: limitations/extract.py")


def discover_directions(field_query: str) -> list[Direction]:
    """Phase 6: corpus build -> extract -> cluster -> openness -> ranked Directions."""
    raise NotImplementedError("Phase 6: directions/cluster.py, directions/openness.py")
