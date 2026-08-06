"""Semantic Scholar / OpenAlex clients.

docs/02-data-sources.md is the source of truth for endpoints, auth, and rate
limits. Everything goes through `rag.http.cached_get` for retry+backoff,
on-disk caching, rate limiting, and polite headers. Language filter to
English only for v1 (see docs/PROGRESS.md scope decision).
"""

from __future__ import annotations

import httpx

from rag.config import settings
from rag.http import cached_get
from rag.models import Paper

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,abstract,year,venue,authors,externalIds"
OPENALEX_BASE = "https://api.openalex.org"


def _s2_headers() -> dict:
    return {"x-api-key": settings.s2_api_key} if settings.s2_api_key else {}


def _paper_from_s2(item: dict | None) -> Paper | None:
    if not item or not item.get("title"):
        return None
    external_ids = item.get("externalIds") or {}
    return Paper(
        id=f"s2:{item['paperId']}",
        doi=external_ids.get("DOI"),
        title=item["title"],
        abstract=item.get("abstract"),
        year=item.get("year"),
        venue=item.get("venue") or None,
        authors=[a.get("name", "") for a in item.get("authors") or []],
    )


def search_papers(query: str, limit: int = 20) -> list[Paper]:
    """Semantic Scholar `/graph/v1/paper/search`, English-filtered."""
    data = cached_get(
        f"{S2_BASE}/paper/search",
        params={"query": query, "limit": limit, "fields": S2_FIELDS},
        headers=_s2_headers(),
        min_interval=1.0,  # ~1 req/s introductory quota per docs/02-data-sources.md
    )
    papers = (_paper_from_s2(item) for item in data.get("data", []))
    return [p for p in papers if p is not None and _looks_english(p)]


def get_paper(paper_id: str) -> Paper | None:
    """Fetch one paper by bare S2 id, or a prefixed external id
    (`DOI:10.xxx`, `ARXIV:xxxx`, ...). Returns None both when the response
    lacks a title AND when S2 simply doesn't have this id indexed (a 404 —
    common for a DOI that Crossref knows but S2 doesn't, e.g. a
    non-arXiv-registered DOI for an otherwise-indexed paper) — a caller
    asking "does S2 have this paper" shouldn't have to distinguish those.
    """
    try:
        data = cached_get(
            f"{S2_BASE}/paper/{paper_id}",
            params={"fields": S2_FIELDS},
            headers=_s2_headers(),
            min_interval=1.0,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    return _paper_from_s2(data)


def _paper_from_openalex(item: dict | None) -> Paper | None:
    if not item:
        return None
    title = item.get("title") or item.get("display_name")
    if not title:
        return None
    authorships = item.get("authorships") or []
    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    doi = (item.get("doi") or "").removeprefix("https://doi.org/") or None
    return Paper(
        id=f"openalex:{item['id'].rsplit('/', 1)[-1]}",
        doi=doi,
        title=title,
        abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
        year=item.get("publication_year"),
        venue=source.get("display_name"),
        authors=[(a.get("author") or {}).get("display_name", "") for a in authorships],
    )


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex returns abstracts as {word: [positions]} to dodge copyright
    reproduction — reassemble the plain text from the position map."""
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def search_papers_openalex(query: str, limit: int = 20) -> list[Paper]:
    """OpenAlex fallback / field-corpus building (language:en filter)."""
    data = cached_get(
        f"{OPENALEX_BASE}/works",
        params={
            "search": query,
            "filter": "language:en",
            "per-page": limit,
            "mailto": settings.contact_email or "",
        },
        min_interval=0.1,  # polite pool is generous with a contact email set
    )
    papers = (_paper_from_openalex(item) for item in data.get("results", []))
    return [p for p in papers if p is not None]


def _looks_english(paper: Paper) -> bool:
    """S2 search results don't expose a language field; cheap ASCII-ratio
    heuristic on the abstract as a stopgap. Revisit with langdetect if this
    proves too noisy once real eval claims are in (docs/03-phase-1-retrieval.md).
    """
    text = paper.abstract or paper.title
    if not text:
        return True
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / len(text) > 0.9
