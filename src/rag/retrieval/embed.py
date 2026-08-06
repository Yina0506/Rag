"""Paper-level + BGE-M3 (passage/claim-level) embeddings.

Model names come from `rag.config.settings` — never hardcode here. Models load
lazily on first use (module-level cache) since they're heavy on an 8GB
machine; see docs/PROGRESS.md "Run stages sequentially, not simultaneously" —
embed/index the corpus fully before loading the LLM for entailment.

Requires the `ml` optional-dependency group: `uv sync --extra ml`.

**Live-verified 2026-08-06**, with a real finding: `allenai/specter2` (the
originally planned model) fails to load via plain `SentenceTransformer` — it's
published in the `adapters`/AdapterHub format, not HuggingFace `peft`
(installing `peft` doesn't fix it; confirmed directly, error changes but
still fails). `settings.paper_embed_model` now defaults to
`sentence-transformers/allenai-specter` — the original SPECTER (v1), built
for the same citation-based paper-similarity objective, packaged as a
directly-loadable checkpoint. Revisit only if implementing real
`adapters`-library loading turns out to matter for eval quality.
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
    """SPECTER embedding for paper-level similarity (title + abstract).

    Not currently used by `retrieval/index.py`'s Qdrant index — that index is
    queried with `embed_text` (a claim), so it's indexed with `embed_text`
    too, to keep query and document vectors in the same space (see
    `index.py`'s module docstring for the live-caught dimension-mismatch bug
    this fixed). Kept here for a genuine paper-to-paper similarity use case,
    should one come up.
    """
    text = f"{title}\n{abstract or ''}".strip()
    vector = _paper_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_text(text: str) -> list[float]:
    """BGE-M3 embedding for claim/passage-level text."""
    vector = _text_model().encode(text, normalize_embeddings=True)
    return vector.tolist()
