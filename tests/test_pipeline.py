"""retrieve_candidates wiring: search -> index -> vector search -> rerank ->
existence gate. verify_claim wiring: retrieve -> entail -> sort -> NOT_FOUND
override. Every stage mocked at its module boundary — this test is about the
glue, not any one stage's internals (those have their own tests)."""

from __future__ import annotations

from rag import pipeline
from rag.models import (
    Candidate,
    Direction,
    ExistenceStatus,
    Grade,
    Limitation,
    LimitationType,
    Paper,
)


def test_retrieve_candidates_returns_empty_when_no_papers_found(mocker) -> None:
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[])

    assert pipeline.retrieve_candidates("a claim with no matches") == []


def test_retrieve_candidates_filters_out_papers_without_abstract(sample_paper, mocker) -> None:
    """Regression (found live via the UI): a paper with no abstract has no
    evidence text for rerank/entailment to reason over, and rerank.py's
    title fallback let a title-only textual match (e.g. a paper literally
    titled after the claim) heavily outscore a genuinely relevant paper —
    cross-encoders reward literal string overlap. Must be filtered before
    reaching rerank/index, not just handled defensively downstream."""
    abstract_less = sample_paper.model_copy(update={"id": "s2:no-abstract", "abstract": None})
    mocker.patch(
        "rag.retrieval.sources.search_papers", return_value=[sample_paper, abstract_less]
    )
    upsert_mock = mocker.patch("rag.retrieval.index.upsert_papers")
    mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.1, 0.2])
    candidate = Candidate(paper=sample_paper, score=0.5)
    mocker.patch("rag.retrieval.index.search", return_value=[candidate])
    mocker.patch("rag.retrieval.rerank.rerank", return_value=[candidate])
    mocker.patch("rag.verify.existence.existence_verdict", return_value=ExistenceStatus.EXISTS)

    pipeline.retrieve_candidates("some claim")

    upserted_papers = upsert_mock.call_args[0][0]
    assert [p.id for p in upserted_papers] == [sample_paper.id]


def test_retrieve_candidates_wires_search_index_rerank_and_gate(sample_paper, mocker) -> None:
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[sample_paper])
    mocker.patch("rag.retrieval.index.upsert_papers")
    mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.1, 0.2])
    candidate = Candidate(paper=sample_paper, score=0.5)
    mocker.patch("rag.retrieval.index.search", return_value=[candidate])
    reranked = mocker.patch("rag.retrieval.rerank.rerank", return_value=[candidate])
    mocker.patch("rag.verify.existence.existence_verdict", return_value=ExistenceStatus.EXISTS)

    result = pipeline.retrieve_candidates("some claim", k=3)

    assert result == [candidate]
    reranked.assert_called_once()


def test_retrieve_candidates_drops_nonexistent_papers(sample_paper, mocker) -> None:
    """The whole trust story: a candidate that fails the existence gate must
    never reach the caller, no matter how it scored upstream."""
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[sample_paper])
    mocker.patch("rag.retrieval.index.upsert_papers")
    mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.1, 0.2])
    candidate = Candidate(paper=sample_paper, score=0.99)
    mocker.patch("rag.retrieval.index.search", return_value=[candidate])
    mocker.patch("rag.retrieval.rerank.rerank", return_value=[candidate])
    mocker.patch("rag.verify.existence.existence_verdict", return_value=ExistenceStatus.NOT_FOUND)

    assert pipeline.retrieve_candidates("some claim") == []


def test_retrieve_candidates_flags_retracted_instead_of_dropping(sample_paper, mocker) -> None:
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[sample_paper])
    mocker.patch("rag.retrieval.index.upsert_papers")
    mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.1, 0.2])
    candidate = Candidate(paper=sample_paper, score=0.9)
    mocker.patch("rag.retrieval.index.search", return_value=[candidate])
    mocker.patch("rag.retrieval.rerank.rerank", return_value=[candidate])
    mocker.patch("rag.verify.existence.existence_verdict", return_value=ExistenceStatus.RETRACTED)

    result = pipeline.retrieve_candidates("some claim")

    assert len(result) == 1
    assert result[0].paper.retracted is True
    assert result[0].paper.id == sample_paper.id
    assert sample_paper.retracted is False  # gate copies, never mutates in place


def test_verify_claim_returns_empty_when_retrieve_candidates_finds_nothing(mocker) -> None:
    mocker.patch.object(pipeline, "retrieve_candidates", return_value=[])

    assert pipeline.verify_claim("claim") == []


def test_verify_claim_builds_graded_verdicts_sorted_best_first(sample_paper, mocker) -> None:
    other_paper = Paper(id="s2:other", title="Another Paper", abstract="unrelated")
    weak_candidate = Candidate(paper=sample_paper, score=0.5)
    strong_candidate = Candidate(paper=other_paper, score=0.5)
    mocker.patch.object(
        pipeline, "retrieve_candidates", return_value=[weak_candidate, strong_candidate]
    )

    def fake_entailer(claim, evidence):
        if "unrelated" in evidence:
            return (Grade.SUPPORTS, 0.95, "supports")
        return (Grade.WEAK, 0.4, "weak")

    mocker.patch("rag.verify.entailment._run_entailer", side_effect=fake_entailer)

    verdicts = pipeline.verify_claim("some claim")

    assert [v.grade for v in verdicts] == [Grade.SUPPORTS, Grade.WEAK]
    assert verdicts[0].paper.id == "s2:other"
    assert verdicts[0].claim.text == "some claim"


def test_verify_claim_overrides_top_grade_to_not_found_below_weak(sample_paper, mocker) -> None:
    """The tool must be willing to say NOT_FOUND rather than present a
    NEUTRAL/CONTRADICTS candidate as if it were a real citation."""
    candidate = Candidate(paper=sample_paper, score=0.5)
    mocker.patch.object(pipeline, "retrieve_candidates", return_value=[candidate])
    mocker.patch(
        "rag.verify.entailment._run_entailer",
        return_value=(Grade.NEUTRAL, 0.6, "on-topic but doesn't establish the claim"),
    )

    verdicts = pipeline.verify_claim("some claim")

    assert len(verdicts) == 1
    assert verdicts[0].grade == Grade.NOT_FOUND
    assert "NEUTRAL" in verdicts[0].justification


def test_verify_claim_does_not_override_when_best_clears_weak(sample_paper, mocker) -> None:
    candidate = Candidate(paper=sample_paper, score=0.5)
    mocker.patch.object(pipeline, "retrieve_candidates", return_value=[candidate])
    mocker.patch(
        "rag.verify.entailment._run_entailer", return_value=(Grade.WEAK, 0.55, "weakly related")
    )

    verdicts = pipeline.verify_claim("some claim")

    assert verdicts[0].grade == Grade.WEAK
    assert verdicts[0].justification == "weakly related"


def test_extract_limitations_returns_empty_when_paper_not_found(mocker) -> None:
    mocker.patch("rag.retrieval.sources.get_paper", return_value=None)

    assert pipeline.extract_limitations("s2:missing") == []


def test_extract_limitations_falls_back_to_abstract_when_no_full_text(sample_paper, mocker) -> None:
    mocker.patch("rag.retrieval.sources.get_paper", return_value=sample_paper)
    mocker.patch("rag.retrieval.fulltext.fetch_full_text", return_value=None)
    extract_mock = mocker.patch("rag.limitations.extract.extract_limitations", return_value=[])

    pipeline.extract_limitations("s2:x")

    extract_mock.assert_called_once_with(sample_paper, sample_paper.abstract)


def test_extract_limitations_flattens_sections_when_available(sample_paper, mocker) -> None:
    mocker.patch("rag.retrieval.sources.get_paper", return_value=sample_paper)
    mocker.patch(
        "rag.retrieval.fulltext.fetch_full_text",
        return_value={"Limitations": "The dataset is small."},
    )
    extract_mock = mocker.patch("rag.limitations.extract.extract_limitations", return_value=[])

    pipeline.extract_limitations("s2:x")

    full_text_arg = extract_mock.call_args[0][1]
    assert "Limitations" in full_text_arg
    assert "The dataset is small." in full_text_arg


def test_discover_directions_wires_corpus_extract_cluster_and_openness(mocker) -> None:
    paper = Paper(id="s2:p1", title="Field Paper", abstract="abstract text")
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[paper])
    limitation = Limitation(paper_id="s2:p1", text="a gap", type=LimitationType.STATED)
    mocker.patch("rag.limitations.extract.extract_limitations", return_value=[limitation])
    unopened = Direction(
        label="a direction", member_limitations=[limitation], frequency=1, still_open=True
    )
    build_mock = mocker.patch("rag.directions.cluster.build_directions", return_value=[unopened])
    opened = unopened.model_copy(update={"still_open": False, "solving_papers": ["s2:fix"]})
    openness_mock = mocker.patch("rag.directions.openness.check_openness", return_value=opened)

    result = pipeline.discover_directions("some field")

    build_mock.assert_called_once_with([limitation])
    openness_mock.assert_called_once_with(unopened)
    assert result == [opened]
