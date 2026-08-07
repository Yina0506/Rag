"""BGE-reranker-v2-m3 cross-encoder over (claim, abstract) pairs.

The biggest lever on mismatch reduction per docs/01-architecture.md — run
after vector search narrows candidates, before they reach the existence gate.
Requires the `ml` optional-dependency group: `uv sync --extra ml`.

**Live-caught bug, fixed upstream**: falling back to `paper.title` when
`abstract` is missing let a title-only textual match (e.g. a paper literally
titled "X Attention Is All You Need") heavily outscore a genuinely relevant
paper whose abstract doesn't repeat the query phrase verbatim — cross-encoders
reward literal string overlap. `pipeline.retrieve_candidates` now filters out
abstract-less papers before they ever reach here, so this fallback shouldn't
normally trigger in production; it's kept only as a defensive default for
direct/standalone calls to `rerank()` (e.g. in tests or a notebook) that
didn't go through that filter.
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
