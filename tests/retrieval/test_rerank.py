"""Assert reranking actually reorders by predicted relevance. The cross-encoder
model itself is mocked out — no ML deps needed for this test."""

from __future__ import annotations

from rag.models import Candidate, Paper
from rag.retrieval import rerank


def _candidate(id_: str, abstract: str, score: float) -> Candidate:
    return Candidate(paper=Paper(id=id_, title=id_, abstract=abstract), score=score)


def test_rerank_reorders_by_cross_encoder_score(mocker) -> None:
    candidates = [
        _candidate("low", "irrelevant abstract", score=0.9),  # high vector score...
        _candidate("high", "directly supports the claim", score=0.5),  # ...but low
    ]
    mock_model = mocker.Mock()
    mock_model.predict.return_value = [0.1, 0.95]  # cross-encoder disagrees with vector score
    mocker.patch.object(rerank, "_reranker", return_value=mock_model)

    result = rerank.rerank("some claim", candidates)

    assert [c.paper.id for c in result] == ["high", "low"]
    assert result[0].score == 0.95


def test_rerank_empty_candidates_returns_empty() -> None:
    assert rerank.rerank("claim", []) == []
