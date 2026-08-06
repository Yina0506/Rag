"""Real tests for extract_stated (pure text logic, no mocking needed).
extract_implicit/extract_limitations mock retrieval/full-text/entailment
since they'd otherwise hit real S2/GROBID/Ollama."""

from __future__ import annotations

from rag.limitations import extract
from rag.models import Grade, Limitation, LimitationType, Paper

FULL_TEXT = """Introduction
This paper studies neural poetry generation using transformers.

Limitations
Our method only works for classical Chinese poetry and does not generalize to other \
languages. The evaluation set is small and may not be representative.

References
Some citation here.
"""


def test_extract_stated_finds_limitations_section() -> None:
    paper = Paper(id="p1", title="Test Paper")

    limitations = extract.extract_stated(paper, FULL_TEXT)

    assert len(limitations) == 2
    assert all(lim.type == LimitationType.STATED for lim in limitations)
    assert all(lim.paper_id == "p1" for lim in limitations)
    assert "classical Chinese poetry" in limitations[0].text


def test_extract_stated_stops_at_next_heading_not_just_limitation_headings() -> None:
    paper = Paper(id="p1", title="Test Paper")

    limitations = extract.extract_stated(paper, FULL_TEXT)

    assert not any("citation" in lim.text for lim in limitations)


def test_extract_stated_recognizes_future_work_and_conclusion_headings() -> None:
    text = "Future Work\nWe plan to extend this to more languages in future work.\n"
    paper = Paper(id="p1", title="Test Paper")

    limitations = extract.extract_stated(paper, text)

    assert len(limitations) == 1


def test_extract_stated_returns_empty_when_no_matching_section() -> None:
    text = "Introduction\nThis is just an intro with no limitations section at all here.\n"
    paper = Paper(id="p1", title="Test Paper")

    assert extract.extract_stated(paper, text) == []


def test_extract_stated_skips_short_fragments() -> None:
    text = "Limitations\nToo short. This one is long enough to count as a real limitation.\n"
    paper = Paper(id="p1", title="Test Paper")

    limitations = extract.extract_stated(paper, text)

    assert len(limitations) == 1
    assert "long enough" in limitations[0].text


def test_extract_implicit_borrows_limitations_from_similar_paper_full_text(mocker) -> None:
    paper = Paper(id="p1", title="Target Paper", abstract="We propose a new method.")
    similar = Paper(id="p2", title="Similar Paper", abstract="A related method.")
    mocker.patch(
        "rag.retrieval.fulltext.fetch_full_text",
        return_value={"Limitations": "The dataset used is small and English-only."},
    )
    mocker.patch("rag.verify.entailment._run_entailer", return_value=(Grade.NEUTRAL, 0.5, "n/a"))

    limitations = extract.extract_implicit(paper, [similar])

    assert any("small and English-only" in lim.text for lim in limitations)
    assert all(lim.type == LimitationType.IMPLICIT for lim in limitations)
    assert all(lim.paper_id == "p1" for lim in limitations)


def test_extract_implicit_flags_contradiction_from_later_paper(mocker) -> None:
    paper = Paper(id="p1", title="Target", abstract="Our method always converges.", year=2020)
    later = Paper(
        id="p2", title="Later Paper", abstract="We show the method can diverge.", year=2023
    )
    mocker.patch("rag.retrieval.fulltext.fetch_full_text", return_value=None)
    mocker.patch(
        "rag.verify.entailment._run_entailer",
        return_value=(Grade.CONTRADICTS, 0.8, "directly contradicts"),
    )

    limitations = extract.extract_implicit(paper, [later])

    assert len(limitations) == 1
    assert "Later work" in limitations[0].text
    assert "p2" in limitations[0].text


def test_extract_implicit_ignores_earlier_papers_for_contradiction_check(mocker) -> None:
    paper = Paper(id="p1", title="Target", abstract="Our method always converges.", year=2023)
    earlier = Paper(id="p2", title="Earlier Paper", abstract="A conflicting claim.", year=2020)
    mocker.patch("rag.retrieval.fulltext.fetch_full_text", return_value=None)
    entailer = mocker.patch("rag.verify.entailment._run_entailer")

    limitations = extract.extract_implicit(paper, [earlier])

    assert limitations == []
    entailer.assert_not_called()


def test_extract_implicit_skips_the_paper_itself_if_present_in_similar_list(mocker) -> None:
    paper = Paper(id="p1", title="Target", abstract="claim")
    mocker.patch("rag.retrieval.fulltext.fetch_full_text")
    entailer = mocker.patch("rag.verify.entailment._run_entailer")

    limitations = extract.extract_implicit(paper, [paper])

    assert limitations == []
    entailer.assert_not_called()


def test_dedupe_drops_near_identical_text() -> None:
    limitations = [
        Limitation(paper_id="p1", text="The dataset is small.", type=LimitationType.STATED),
        Limitation(paper_id="p1", text="The dataset is small!", type=LimitationType.STATED),
        Limitation(
            paper_id="p1", text="Completely different limitation here.", type=LimitationType.STATED
        ),
    ]

    deduped = extract._dedupe(limitations)

    assert len(deduped) == 2


def test_extract_limitations_skips_implicit_when_stated_is_plentiful(mocker) -> None:
    paper = Paper(id="p1", title="Test Paper")
    find_similar = mocker.patch.object(extract, "_find_similar_papers")
    mocker.patch.object(extract, "_with_topic_embedding", side_effect=lambda lim: lim)

    text = (
        "Limitations\nThe dataset only covers English text. "
        "Our runtime scales quadratically with input length.\n"
    )
    result = extract.extract_limitations(paper, text)

    assert len(result) == 2
    find_similar.assert_not_called()


def test_extract_limitations_pursues_implicit_when_stated_is_sparse(mocker) -> None:
    paper = Paper(id="p1", title="Test Paper")
    mocker.patch.object(extract, "_find_similar_papers", return_value=[])
    mocker.patch.object(extract, "_with_topic_embedding", side_effect=lambda lim: lim)
    implicit_mock = mocker.patch.object(extract, "extract_implicit", return_value=[])

    extract.extract_limitations(paper, "Introduction\nNo limitations section here.\n")

    implicit_mock.assert_called_once()


def test_extract_limitations_attaches_topic_embedding(mocker) -> None:
    paper = Paper(id="p1", title="Test Paper")
    mocker.patch.object(extract, "_find_similar_papers", return_value=[])
    mocker.patch("rag.retrieval.embed.embed_text", return_value=[0.1, 0.2, 0.3])

    text = "Limitations\nA single clear limitation statement goes right here.\n"
    result = extract.extract_limitations(paper, text)

    assert len(result) == 1
    assert result[0].topic_embedding == [0.1, 0.2, 0.3]
