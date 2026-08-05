"""The entrypoints the UI (and CLI/tests) call. Keep this the single place that
wires retrieval -> existence gate -> entailment together, per module.

Implement incrementally, one phase at a time (docs/03..08):
- verify_claim          Phase 1 (retrieval-only stub) -> Phase 2 (+ gate) -> Phase 3 (+ entailment)
- audit_draft           Phase 4
- extract_limitations   Phase 5
- discover_directions   Phase 6
"""

from __future__ import annotations

from rag.models import Candidate, Direction, ExistenceStatus, Limitation


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


def verify_claim(claim: str, k: int = 5) -> list[Candidate]:
    """Phase 1-2: retrieval + existence-gated, still ungraded. Phase 3
    upgrades the return type to graded Verdicts (retrieve -> gate -> entail ->
    sort). Callers written against this signature will need to update then —
    that's expected.
    """
    return retrieve_candidates(claim, k=k)


def audit_draft(path: str) -> dict:
    """Phase 4: ingest a draft (PDF/.bib/.tex), audit every (claim, citation) pair."""
    raise NotImplementedError("Phase 4: audit/draft.py")


def extract_limitations(paper_id: str) -> list[Limitation]:
    """Phase 5: stated + implicit limitations for one paper."""
    raise NotImplementedError("Phase 5: limitations/extract.py")


def discover_directions(field_query: str) -> list[Direction]:
    """Phase 6: corpus build -> extract -> cluster -> openness -> ranked Directions."""
    raise NotImplementedError("Phase 6: directions/cluster.py, directions/openness.py")
