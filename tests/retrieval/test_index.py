"""Phase 1. Qdrant upsert/search roundtrip against the embedded local index."""

import pytest


@pytest.mark.xfail(reason="Phase 1: implement rag.retrieval.index", strict=False)
def test_upsert_then_search_roundtrip(sample_paper) -> None:
    from rag.retrieval.index import ensure_collection, upsert_papers

    ensure_collection()
    upsert_papers([sample_paper])
