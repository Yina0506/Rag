"""The existence gate — a single, non-bypassable choke point (docs/04-phase-2).

Every paper leaving the pipeline must resolve to a real DOI/ID via Crossref and
be checked against retraction data. Nothing downstream trusts a paper this
module hasn't cleared. Cache Crossref lookups; they're the hot path.
"""

from __future__ import annotations

from rag.models import ExistenceStatus, Paper


def resolve_doi(paper: Paper) -> bool:
    """Crossref (and S2 id fallback) DOI resolution."""
    raise NotImplementedError("Phase 2")


def is_retracted(paper: Paper) -> bool:
    """Retraction Watch / Crossref retraction metadata."""
    raise NotImplementedError("Phase 2")


def existence_verdict(paper: Paper) -> ExistenceStatus:
    raise NotImplementedError("Phase 2")
