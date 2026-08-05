"""The gate is load-bearing: a fabricated paper must always be rejected, a
retracted one must always be flagged. No real network — mock `cached_get`."""

from __future__ import annotations

import httpx

from rag.models import ExistenceStatus, Paper
from rag.verify import existence


def _not_found(url, **kwargs):
    request = httpx.Request("GET", url)
    response = httpx.Response(404, request=request)
    raise httpx.HTTPStatusError("not found", request=request, response=response)


def test_fabricated_paper_is_rejected(mocker) -> None:
    mocker.patch.object(existence, "cached_get", side_effect=_not_found)
    fake = Paper(id="fake:1", doi="10.9999/does-not-exist", title="Fabricated Paper Title")

    assert existence.existence_verdict(fake) == ExistenceStatus.NOT_FOUND


def test_real_doi_resolves_to_exists(mocker) -> None:
    mocker.patch.object(existence, "cached_get", return_value={"message": {"DOI": "10.1000/real"}})
    real = Paper(id="s2:1", doi="10.1000/real", title="A Real Paper")

    assert existence.existence_verdict(real) == ExistenceStatus.EXISTS


def test_retracted_paper_is_flagged(mocker) -> None:
    mocker.patch.object(
        existence,
        "cached_get",
        return_value={
            "message": {"DOI": "10.1000/retracted", "update-to": [{"type": "retraction"}]}
        },
    )
    retracted = Paper(id="s2:2", doi="10.1000/retracted", title="A Retracted Paper")

    assert existence.existence_verdict(retracted) == ExistenceStatus.RETRACTED


def test_retraction_via_relation_field_is_also_caught(mocker) -> None:
    mocker.patch.object(
        existence,
        "cached_get",
        return_value={
            "message": {
                "DOI": "10.1000/retracted2",
                "relation": {"is-retracted-by": [{"id": "10.1000/notice"}]},
            }
        },
    )
    retracted = Paper(id="s2:3", doi="10.1000/retracted2", title="Also Retracted")

    assert existence.is_retracted(retracted) is True


def test_doi_less_paper_falls_back_to_s2_lookup(mocker) -> None:
    mocker.patch.object(existence.sources, "get_paper", return_value=Paper(id="s2:4", title="x"))
    no_doi = Paper(id="s2:4", title="A Preprint With No Registered DOI")

    assert existence.resolve_doi(no_doi) is True


def test_doi_less_paper_not_found_via_s2_is_rejected(mocker) -> None:
    mocker.patch.object(existence.sources, "get_paper", return_value=None)
    no_doi = Paper(id="s2:5", title="Doesn't Actually Exist")

    assert existence.resolve_doi(no_doi) is False


def test_non_404_http_errors_propagate_instead_of_being_swallowed(mocker) -> None:
    def _server_error(url, **kwargs):
        request = httpx.Request("GET", url)
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError("server error", request=request, response=response)

    mocker.patch.object(existence, "cached_get", side_effect=_server_error)
    paper = Paper(id="s2:6", doi="10.1000/whatever", title="x")

    try:
        existence.resolve_doi(paper)
        raised = False
    except httpx.HTTPStatusError:
        raised = True
    assert raised


def test_fuzzy_match_existence_accepts_close_title(mocker) -> None:
    mocker.patch.object(
        existence,
        "cached_get",
        return_value={
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/matched",
                        "title": ["Evaluating Neural Poetry Generation in Chinese"],
                        "author": [{"given": "A.", "family": "Author"}],
                        "published-print": {"date-parts": [[2023]]},
                    }
                ]
            }
        },
    )

    matched = existence.fuzzy_match_existence("Evaluating Neural Poetry Generation in Chinese")

    assert matched is not None
    assert matched.doi == "10.1000/matched"


def test_fuzzy_match_existence_rejects_unrelated_title(mocker) -> None:
    mocker.patch.object(
        existence,
        "cached_get",
        return_value={
            "message": {"items": [{"DOI": "10.1000/unrelated", "title": ["Something Else"]}]}
        },
    )

    matched = existence.fuzzy_match_existence("Evaluating Neural Poetry Generation in Chinese")

    assert matched is None
