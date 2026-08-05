"""Semantic Scholar / OpenAlex / arXiv clients.

docs/02-data-sources.md is the source of truth for endpoints, auth, and rate
limits. Build in from day one: shared HTTP client with retry+backoff, an
on-disk response cache, a rate limiter, and a polite User-Agent / x-api-key.
Language filter to English only for v1 (see docs/PROGRESS.md scope decision).
"""

from __future__ import annotations

from rag.models import Paper


def search_papers(query: str, limit: int = 20) -> list[Paper]:
    """Semantic Scholar `/graph/v1/paper/search`, English-filtered."""
    raise NotImplementedError("Phase 1")


def get_paper(paper_id: str) -> Paper | None:
    """Fetch one paper by S2/DOI id."""
    raise NotImplementedError("Phase 1")


def search_papers_openalex(query: str, limit: int = 20) -> list[Paper]:
    """OpenAlex fallback / field-corpus building (language:en filter)."""
    raise NotImplementedError("Phase 1")
