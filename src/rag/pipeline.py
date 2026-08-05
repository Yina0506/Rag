"""The entrypoints the UI (and CLI/tests) call. Keep this the single place that
wires retrieval -> existence gate -> entailment together, per module.

Implement incrementally, one phase at a time (docs/03..08):
- verify_claim          Phase 1 (retrieval-only stub) -> Phase 2 (+ gate) -> Phase 3 (+ entailment)
- audit_draft           Phase 4
- extract_limitations   Phase 5
- discover_directions   Phase 6
"""

from __future__ import annotations

from rag.models import Candidate, Direction, Limitation, Verdict


def verify_claim(claim: str, k: int = 5) -> list[Verdict]:
    """Retrieve candidates, gate for existence, grade by entailment. Returns
    graded Verdicts (may be empty / NOT_FOUND — abstaining is correct, not a bug).
    """
    raise NotImplementedError("Phase 1: wire retrieve_candidates first")


def retrieve_candidates(claim: str, k: int = 5) -> list[Candidate]:
    """Phase 1 stub: API search -> embed -> index/search -> rerank -> top-k."""
    raise NotImplementedError("Phase 1: retrieval/sources.py, index.py, rerank.py")


def audit_draft(path: str) -> dict:
    """Phase 4: ingest a draft (PDF/.bib/.tex), audit every (claim, citation) pair."""
    raise NotImplementedError("Phase 4: audit/draft.py")


def extract_limitations(paper_id: str) -> list[Limitation]:
    """Phase 5: stated + implicit limitations for one paper."""
    raise NotImplementedError("Phase 5: limitations/extract.py")


def discover_directions(field_query: str) -> list[Direction]:
    """Phase 6: corpus build -> extract -> cluster -> openness -> ranked Directions."""
    raise NotImplementedError("Phase 6: directions/cluster.py, directions/openness.py")
