"""retrieve_candidates wiring: search -> index -> vector search -> rerank.
Every stage mocked at its module boundary — this test is about the glue,
not any one stage's internals (those have their own tests)."""

from __future__ import annotations

from rag import pipeline
from rag.models import Candidate


def test_retrieve_candidates_returns_empty_when_no_papers_found(mocker) -> None:
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[])

    assert pipeline.retrieve_candidates("a claim with no matches") == []


def test_retrieve_candidates_wires_search_index_and_rerank(sample_paper, mocker) -> None:
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[sample_paper])
    mocker.patch("rag.retrieval.index.upsert_papers")
    mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.1, 0.2])
    candidate = Candidate(paper=sample_paper, score=0.5)
    mocker.patch("rag.retrieval.index.search", return_value=[candidate])
    reranked = mocker.patch("rag.retrieval.rerank.rerank", return_value=[candidate])

    result = pipeline.retrieve_candidates("some claim", k=3)

    assert result == [candidate]
    reranked.assert_called_once()


def test_verify_claim_is_currently_an_alias_for_retrieve_candidates(mocker) -> None:
    mock_retrieve = mocker.patch.object(pipeline, "retrieve_candidates", return_value=[])

    pipeline.verify_claim("claim", k=7)

    mock_retrieve.assert_called_once_with("claim", k=7)
