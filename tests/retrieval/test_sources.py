"""Phase 1. Mock httpx here — no real network calls in unit tests."""

import pytest


@pytest.mark.xfail(reason="Phase 1: implement rag.retrieval.sources", strict=False)
def test_search_papers_returns_english_results() -> None:
    from rag.retrieval.sources import search_papers

    search_papers("neural poetry generation evaluation")
