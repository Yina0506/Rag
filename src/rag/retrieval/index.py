"""Qdrant wrapper: create collection, upsert papers, filtered vector search.

Two modes via `settings.qdrant_mode` (docs/01-architecture.md):
- "embedded": local on-disk Qdrant at `data/qdrant` — no docker, default for dev.
- "server": talk to the `qdrant` service from docker-compose.yml.

**Live-caught bug**: papers were indexed with `embed_paper` (SPECTER, 768-dim)
but `pipeline.retrieve_candidates` queries with `embed_text` (BGE-M3,
1024-dim) — two different models' vector spaces aren't directly comparable,
and Qdrant can't even compute a distance between mismatched dimensions
(`ValueError: shapes (n,768) and (1024,) not aligned`). This was invisible
in unit tests (which always mock the embedding calls) and wasn't caught by
this session's earlier live tests of `embed_paper`/`embed_text` individually
— it only surfaced once `retrieve_candidates` ran fully live end-to-end for
the first time. Fixed by indexing papers with `embed_text` too, so the
query vector and the indexed document vectors share one embedding space.
`embed_paper` (SPECTER) is still available in `retrieval/embed.py` for a
genuine paper-to-paper similarity use case if one comes up (e.g. upgrading
`limitations._find_similar_papers` from keyword search to vector search) —
just not used for this index.

**Second live-caught bug**: `get_client()` used to construct a brand new
`QdrantClient` on every call. Embedded-mode Qdrant takes an exclusive file
lock on `data/qdrant` for the life of the client object; a long-running
process (the Streamlit app) calling `retrieve_candidates` more than once
could race its own previous client's lock release against the new client's
acquisition, surfacing as "Storage folder ... is already accessed by
another instance of Qdrant client" — a process conflicting with *itself*.
Fixed by caching the client (one instance for the process's lifetime,
matching the `@lru_cache` singleton pattern already used for the embedding/
reranker models). For genuine multi-process concurrent access (e.g. this
UI plus a separate script both touching the index at once), embedded mode
is still the wrong tool — switch to `qdrant_mode = "server"` and run the
`qdrant` service from docker-compose.yml, which is built for exactly that.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from rag.config import settings
from rag.models import Candidate, Paper
from rag.retrieval.embed import embed_text

VECTOR_SIZE = 1024  # BAAI/bge-m3 embedding dimension — must match the query embedding space


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    if settings.qdrant_mode == "server":
        return QdrantClient(url=settings.qdrant_url)
    return QdrantClient(path=str(settings.data_path / "qdrant"))


def ensure_collection(client: QdrantClient | None = None) -> QdrantClient:
    client = client or get_client()
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qm.VectorParams(size=VECTOR_SIZE, distance=qm.Distance.COSINE),
        )
    return client


def upsert_papers(papers: list[Paper], client: QdrantClient | None = None) -> None:
    client = ensure_collection(client)
    points = [
        qm.PointStruct(
            id=_point_id(paper.id),
            vector=embed_text(f"{paper.title}\n{paper.abstract or ''}".strip()),
            payload=paper.model_dump(),
        )
        for paper in papers
    ]
    if points:
        client.upsert(collection_name=settings.qdrant_collection, points=points)


def search(
    query_vector: list[float],
    k: int = 20,
    filters: dict | None = None,
    client: QdrantClient | None = None,
) -> list[Candidate]:
    client = ensure_collection(client)
    hits = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=k,
        query_filter=_build_filter(filters) if filters else None,
    ).points
    return [Candidate(paper=Paper.model_validate(hit.payload), score=hit.score) for hit in hits]


def _point_id(paper_id: str) -> str:
    """Qdrant point ids must be an unsigned int or a UUID — hash the paper id
    (e.g. "s2:abc123") into a stable UUID5 so upserts are idempotent."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, paper_id))


def _build_filter(filters: dict) -> qm.Filter:
    must: list[qm.Condition] = []
    if "year_gte" in filters or "year_lte" in filters:
        must.append(
            qm.FieldCondition(
                key="year",
                range=qm.Range(gte=filters.get("year_gte"), lte=filters.get("year_lte")),
            )
        )
    if "venue" in filters:
        must.append(qm.FieldCondition(key="venue", match=qm.MatchValue(value=filters["venue"])))
    return qm.Filter(must=must)
