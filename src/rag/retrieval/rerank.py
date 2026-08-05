"""BGE-reranker-v2-m3 cross-encoder over (claim, abstract) pairs.

The biggest lever on mismatch reduction per docs/01-architecture.md — run
after vector search narrows candidates, before they reach the existence gate.
Requires the `ml` optional-dependency group: `uv sync --extra ml`.
"""

from __future__ import annotations

from functools import lru_cache

from rag.config import settings
from rag.models import Candidate


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.reranker_model)


def rerank(claim: str, candidates: list[Candidate]) -> list[Candidate]:
    if not candidates:
        return []
    pairs = [(claim, c.paper.abstract or c.paper.title) for c in candidates]
    scores = _reranker().predict(pairs)
    reranked = [
        c.model_copy(update={"score": float(s)})
        for c, s in zip(candidates, scores, strict=True)
    ]
    reranked.sort(key=lambda c: c.score, reverse=True)
    return reranked
