"""No real network calls — mock `cached_get` at the module boundary."""

from __future__ import annotations

from rag.retrieval import sources

S2_SEARCH_RESPONSE = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Evaluating Neural Poetry Generation in Chinese",
            "abstract": "We propose a benchmark for evaluating LLM-generated classical "
            "Chinese poetry.",
            "year": 2023,
            "venue": "ICCC",
            "authors": [{"name": "A. Author"}, {"name": "B. Author"}],
            "externalIds": {"DOI": "10.1000/abc123"},
        },
        {
            "paperId": "def456",
            "title": None,  # missing title -> must be dropped, not crash
            "abstract": "irrelevant",
            "year": 2022,
        },
    ]
}

OPENALEX_SEARCH_RESPONSE = {
    "results": [
        {
            "id": "https://openalex.org/W123",
            "title": "A Study of Tang Poetry Generation",
            "doi": "https://doi.org/10.1000/xyz789",
            "publication_year": 2021,
            "primary_location": {"source": {"display_name": "LREC"}},
            "authorships": [{"author": {"display_name": "C. Author"}}],
            "abstract_inverted_index": {"We": [0], "study": [1], "poetry": [2]},
        }
    ]
}


def test_search_papers_parses_and_drops_titleless_results(mocker) -> None:
    mocker.patch.object(sources, "cached_get", return_value=S2_SEARCH_RESPONSE)

    papers = sources.search_papers("neural poetry generation evaluation")

    assert len(papers) == 1
    paper = papers[0]
    assert paper.id == "s2:abc123"
    assert paper.doi == "10.1000/abc123"
    assert paper.year == 2023
    assert paper.authors == ["A. Author", "B. Author"]


def test_search_papers_sends_api_key_header_when_configured(mocker) -> None:
    mock_get = mocker.patch.object(sources, "cached_get", return_value={"data": []})
    mocker.patch.object(sources.settings, "s2_api_key", "secret-key")

    sources.search_papers("query")

    _, kwargs = mock_get.call_args
    assert kwargs["headers"] == {"x-api-key": "secret-key"}


def test_search_papers_openalex_reconstructs_abstract_and_doi(mocker) -> None:
    mocker.patch.object(sources, "cached_get", return_value=OPENALEX_SEARCH_RESPONSE)

    papers = sources.search_papers_openalex("Tang poetry generation")

    assert len(papers) == 1
    paper = papers[0]
    assert paper.id == "openalex:W123"
    assert paper.doi == "10.1000/xyz789"
    assert paper.venue == "LREC"
    assert paper.abstract == "We study poetry"


def test_looks_english_flags_mostly_non_ascii_abstract() -> None:
    from rag.models import Paper

    non_english = Paper(id="x", title="t", abstract="这是一个中文摘要，用于测试语言过滤器")
    english = Paper(id="y", title="t", abstract="This is an English abstract for testing.")

    assert sources._looks_english(english) is True
    assert sources._looks_english(non_english) is False
