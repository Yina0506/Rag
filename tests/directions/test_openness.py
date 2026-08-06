"""No real network/LLM — mock at the module boundary."""

from __future__ import annotations

from rag.directions import openness
from rag.models import Direction, Grade, Limitation, LimitationType, Paper


def _direction(member_paper_ids: list[str], label: str = "Some open gap") -> Direction:
    return Direction(
        label=label,
        member_limitations=[
            Limitation(paper_id=pid, text="a limitation", type=LimitationType.STATED)
            for pid in member_paper_ids
        ],
        frequency=len(member_paper_ids),
        still_open=True,
        solving_papers=[],
    )


def test_find_later_papers_filters_by_cutoff_year(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch(
        "rag.retrieval.sources.get_paper",
        return_value=Paper(id="s2:raiser1", title="Raiser", year=2020),
    )
    citing_old = Paper(id="s2:old", title="Old citing paper", year=2019)
    citing_new = Paper(id="s2:new", title="New citing paper", year=2023)
    mocker.patch(
        "rag.retrieval.sources.get_citing_papers", return_value=[citing_old, citing_new]
    )
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[])

    later = openness.find_later_papers(direction)

    assert later == ["s2:new"]


def test_find_later_papers_includes_topical_search_results(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch(
        "rag.retrieval.sources.get_paper",
        return_value=Paper(id="s2:raiser1", title="Raiser", year=2020),
    )
    mocker.patch("rag.retrieval.sources.get_citing_papers", return_value=[])
    topical_hit = Paper(id="s2:topical", title="A later paper on the same gap", year=2024)
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[topical_hit])

    later = openness.find_later_papers(direction)

    assert later == ["s2:topical"]


def test_find_later_papers_with_no_known_years_keeps_everything(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch("rag.retrieval.sources.get_paper", return_value=None)  # year unknown
    citing = Paper(id="s2:any", title="Any year", year=None)
    mocker.patch("rag.retrieval.sources.get_citing_papers", return_value=[citing])
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[])

    assert openness.find_later_papers(direction) == ["s2:any"]


def test_check_openness_marks_still_open_when_no_later_paper_resolves_it(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch.object(openness, "find_later_papers", return_value=["s2:later1"])
    mocker.patch(
        "rag.retrieval.sources.get_paper",
        return_value=Paper(id="s2:later1", title="Unrelated later paper", abstract="unrelated"),
    )
    mocker.patch(
        "rag.verify.entailment._run_entailer",
        return_value=(Grade.NEUTRAL, 0.5, "does not address the gap"),
    )

    result = openness.check_openness(direction)

    assert result.still_open is True
    assert result.solving_papers == []


def test_check_openness_marks_resolved_when_later_paper_supports_the_fix(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch.object(openness, "find_later_papers", return_value=["s2:later1"])
    mocker.patch(
        "rag.retrieval.sources.get_paper",
        return_value=Paper(id="s2:later1", title="Fix paper", abstract="We solve this gap."),
    )
    mocker.patch(
        "rag.verify.entailment._run_entailer",
        return_value=(Grade.SUPPORTS, 0.9, "directly addresses the gap"),
    )

    result = openness.check_openness(direction)

    assert result.still_open is False
    assert result.solving_papers == ["s2:later1"]


def test_check_openness_skips_papers_without_abstracts(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch.object(openness, "find_later_papers", return_value=["s2:later1"])
    mocker.patch(
        "rag.retrieval.sources.get_paper", return_value=Paper(id="s2:later1", title="No abstract")
    )
    entailer = mocker.patch("rag.verify.entailment._run_entailer")

    result = openness.check_openness(direction)

    assert result.still_open is True
    entailer.assert_not_called()


def test_check_openness_does_not_mutate_original_direction(mocker) -> None:
    direction = _direction(["s2:raiser1"])
    mocker.patch.object(openness, "find_later_papers", return_value=[])

    result = openness.check_openness(direction)

    assert result is not direction
    assert direction.still_open is True  # original untouched
