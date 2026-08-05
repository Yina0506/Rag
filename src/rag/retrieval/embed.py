"""SPECTER2 (paper-level) + BGE-M3 (passage/claim-level) embeddings.

Model names come from `rag.config.settings` — never hardcode here. Models load
lazily on first use (module-level cache) since they're heavy on an 8GB
machine; see docs/PROGRESS.md "Run stages sequentially, not simultaneously" —
embed/index the corpus fully before loading the LLM for entailment.

Requires the `ml` optional-dependency group: `uv sync --extra ml`.

Note: `allenai/specter2` is published as an adapter on top of a base
transformer (needs the `adapters` package for its proximity-mode adapter to
get the true SPECTER2 behavior). Loading it here as a plain
`sentence-transformers` model is a reasonable Phase 1 starting point; revisit
if eval shows paper-similarity quality is off.
"""

from __future__ import annotations

from functools import lru_cache

from rag.config import settings


@lru_cache(maxsize=1)
def _paper_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.paper_embed_model)


@lru_cache(maxsize=1)
def _text_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.text_embed_model)


def embed_paper(title: str, abstract: str | None) -> list[float]:
    """SPECTER2 embedding for paper-level similarity (title + abstract)."""
    text = f"{title}\n{abstract or ''}".strip()
    vector = _paper_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_text(text: str) -> list[float]:
    """BGE-M3 embedding for claim/passage-level text."""
    vector = _text_model().encode(text, normalize_embeddings=True)
    return vector.tolist()
