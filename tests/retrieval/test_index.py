"""Qdrant upsert/search roundtrip against an in-memory client — no docker,
no ML deps needed (embed_paper is mocked to a deterministic vector)."""

from __future__ import annotations

from qdrant_client import QdrantClient

from rag.retrieval import index


def _memory_client() -> QdrantClient:
    return QdrantClient(":memory:")


def test_upsert_then_search_roundtrip(sample_paper, mocker) -> None:
    mocker.patch.object(index, "embed_paper", return_value=[0.1] * index.VECTOR_SIZE)
    client = _memory_client()

    index.upsert_papers([sample_paper], client=client)
    results = index.search([0.1] * index.VECTOR_SIZE, k=5, client=client)

    assert len(results) == 1
    assert results[0].paper.id == sample_paper.id
    assert results[0].score > 0.99


def test_point_id_is_stable_for_idempotent_upserts() -> None:
    assert index._point_id("s2:abc123") == index._point_id("s2:abc123")
    assert index._point_id("s2:abc123") != index._point_id("s2:other")


def test_search_applies_year_filter(sample_paper, mocker) -> None:
    mocker.patch.object(index, "embed_paper", return_value=[0.1] * index.VECTOR_SIZE)
    client = _memory_client()
    index.upsert_papers([sample_paper], client=client)  # year=2024

    in_range = index.search([0.1] * index.VECTOR_SIZE, filters={"year_gte": 2020}, client=client)
    out_of_range = index.search(
        [0.1] * index.VECTOR_SIZE, filters={"year_gte": 2030}, client=client
    )

    assert len(in_range) == 1
    assert len(out_of_range) == 0
