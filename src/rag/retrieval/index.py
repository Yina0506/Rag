"""Qdrant wrapper: create collection, upsert papers, filtered vector search.

Two modes via `settings.qdrant_mode`:
- "embedded": local on-disk Qdrant at `settings.qdrant_path` — no docker, good
  for Phase 1 dev (see docs/03-phase-1-retrieval.md notes).
- "server": talk to the `qdrant` service from docker-compose.yml at
  `settings.qdrant_url` — used for deployment.
"""

from __future__ import annotations

from qdrant_client import QdrantClient

from rag.config import settings
from rag.models import Candidate, Paper


def get_client() -> QdrantClient:
    if settings.qdrant_mode == "server":
        return QdrantClient(url=settings.qdrant_url)
    return QdrantClient(path=str(settings.data_path / "qdrant"))


def ensure_collection(client: QdrantClient | None = None) -> None:
    raise NotImplementedError("Phase 1")


def upsert_papers(papers: list[Paper], client: QdrantClient | None = None) -> None:
    raise NotImplementedError("Phase 1")


def search(query_vector: list[float], k: int = 20, filters: dict | None = None) -> list[Candidate]:
    raise NotImplementedError("Phase 1")
