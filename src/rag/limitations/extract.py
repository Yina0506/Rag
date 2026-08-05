"""Stated + implicit limitation extraction (docs/07-phase-5-limitation-extraction.md).

Stated: locate Limitations / Future Work / Conclusion sections, extract spans.
Implicit (the valuable part, per BAGELS): for a paper lacking/underreporting
limitations, retrieve similar papers and surface limitations they raise that
plausibly apply, and detect later papers that CONTRADICT this paper's claims
(reuses `verify.entailment`).
"""

from __future__ import annotations

from rag.models import Limitation, Paper


def extract_stated(paper: Paper, full_text: str) -> list[Limitation]:
    raise NotImplementedError("Phase 5")


def extract_implicit(paper: Paper, similar_papers: list[Paper]) -> list[Limitation]:
    raise NotImplementedError("Phase 5")


def extract_limitations(paper: Paper, full_text: str) -> list[Limitation]:
    """Stated + implicit, deduped, each normalized with a topic embedding."""
    raise NotImplementedError("Phase 5")
