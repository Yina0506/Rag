"""Phase 1. Assert reranking actually reorders by (claim, abstract) relevance."""

import pytest


@pytest.mark.xfail(reason="Phase 1: implement rag.retrieval.rerank", strict=False)
def test_rerank_orders_by_relevance() -> None:
    from rag.retrieval.rerank import rerank

    rerank("claim text", [])
