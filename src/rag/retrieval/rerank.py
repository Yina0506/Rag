"""BGE-reranker-v2-m3 cross-encoder over (claim, abstract) pairs.

The biggest lever on mismatch reduction per docs/01-architecture.md — run this
after vector search narrows candidates, before they reach the existence gate.
"""

from __future__ import annotations

from rag.models import Candidate


def rerank(claim: str, candidates: list[Candidate]) -> list[Candidate]:
    raise NotImplementedError("Phase 1")
