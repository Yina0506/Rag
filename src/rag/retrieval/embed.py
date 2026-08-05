"""SPECTER2 (paper-level) + BGE-M3 (passage/claim-level) embeddings.

Model names come from `rag.config.settings` — never hardcode here. Load lazily
(module-level singletons) since these are heavy on an 8GB machine; see
docs/PROGRESS.md "Run stages sequentially, not simultaneously."
"""

from __future__ import annotations


def embed_paper(title: str, abstract: str | None) -> list[float]:
    """SPECTER2 embedding for paper-level similarity."""
    raise NotImplementedError("Phase 1")


def embed_text(text: str) -> list[float]:
    """BGE-M3 embedding for claim/passage-level text."""
    raise NotImplementedError("Phase 1")
