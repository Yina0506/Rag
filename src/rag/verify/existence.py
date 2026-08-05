"""The existence gate — a single, non-bypassable choke point (docs/04-phase-2).

Every paper leaving the pipeline must resolve to a real DOI/ID via Crossref and
be checked against retraction data. Nothing downstream trusts a paper this
module hasn't cleared. `rag.pipeline.retrieve_candidates` is where the gate is
actually wired in (docs/04's "single choke point in pipeline.py").

Crossref lookups go through `rag.http.cached_get`, so repeated dev runs don't
re-hit the network — see docs/04-phase-2-existence-gate.md "cache Crossref
lookups; they're the hot path."
"""

from __future__ import annotations

import difflib

import httpx

from rag.http import cached_get
from rag.models import ExistenceStatus, Paper
from rag.retrieval import sources

CROSSREF_WORKS = "https://api.crossref.org/works"


def _crossref_work(doi: str) -> dict | None:
    """Crossref work metadata for a DOI, or None if it doesn't resolve."""
    try:
        data = cached_get(f"{CROSSREF_WORKS}/{doi}", min_interval=0.5)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    return data.get("message")


def resolve_doi(paper: Paper) -> bool:
    """Crossref DOI resolution, with an S2-id fallback for DOI-less candidates
    (a real S2 paper without a registered DOI — preprints, some workshop
    papers — still counts as existing)."""
    if paper.doi:
        return _crossref_work(paper.doi) is not None
    if paper.id.startswith("s2:"):
        return sources.get_paper(paper.id.removeprefix("s2:")) is not None
    return False


def is_retracted(paper: Paper) -> bool:
    """A work is retracted if Crossref links it to a retraction notice via the
    `update-to` metadata or the `is-retracted-by` relation. DOI-less papers
    can't be checked this way — they fall back to `resolve_doi`'s weaker S2
    existence check and are never flagged retracted (known gap, not silent:
    see docs/04-phase-2-existence-gate.md)."""
    if not paper.doi:
        return False
    work = _crossref_work(paper.doi)
    if not work:
        return False
    if any(u.get("type") == "retraction" for u in work.get("update-to") or []):
        return True
    relation = work.get("relation") or {}
    return bool(relation.get("is-retracted-by"))


def existence_verdict(paper: Paper) -> ExistenceStatus:
    """The single hard verdict every candidate must clear before presentation."""
    if is_retracted(paper):
        return ExistenceStatus.RETRACTED
    if resolve_doi(paper):
        return ExistenceStatus.EXISTS
    return ExistenceStatus.NOT_FOUND


def _titles_match(a: str, b: str, threshold: float = 0.85) -> bool:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def _paper_from_crossref(item: dict) -> Paper:
    title = " ".join(item.get("title") or [])
    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author") or []
    ]
    date_parts = (
        (item.get("published-print") or item.get("published-online") or {}).get("date-parts")
        or [[None]]
    )[0]
    return Paper(
        id=f"doi:{item.get('DOI')}",
        doi=item.get("DOI"),
        title=title,
        year=date_parts[0],
        authors=authors,
    )


def fuzzy_match_existence(
    title: str, authors: list[str] | None = None, year: int | None = None
) -> Paper | None:
    """For an LLM-suggested title with no DOI (the Phase 4 draft-audit case):
    query Crossref's bibliographic search and only trust a result whose title
    is a close match. Returns the matched real Paper, or None if nothing was
    confident enough to trust — never guesses.
    """
    query = f"{title} {' '.join(authors)}" if authors else title
    data = cached_get(
        CROSSREF_WORKS, params={"query.bibliographic": query, "rows": 3}, min_interval=0.5
    )
    for item in data.get("message", {}).get("items", []):
        candidate_title = " ".join(item.get("title") or [])
        if _titles_match(title, candidate_title):
            matched = _paper_from_crossref(item)
            if year is not None and matched.year is not None and abs(matched.year - year) > 1:
                continue
            return matched
    return None
