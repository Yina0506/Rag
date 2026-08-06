"""Qdrant wrapper: create collection, upsert papers, filtered vector search.

Two modes via `settings.qdrant_mode` (docs/01-architecture.md):
- "embedded": local on-disk Qdrant at `data/qdrant` — no docker, default for dev.
- "server": talk to the `qdrant` service from docker-compose.yml.

Paper vectors are SPECTER (`retrieval.embed.embed_paper`); `VECTOR_SIZE` must
match that model's output dimension.
"""

from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from rag.config import settings
from rag.models import Candidate, Paper
from rag.retrieval.embed import embed_paper

VECTOR_SIZE = 768  # sentence-transformers/allenai-specter embedding dimension


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
            vector=embed_paper(paper.title, paper.abstract),
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
