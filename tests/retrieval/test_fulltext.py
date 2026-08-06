"""parse_sections/_extract_arxiv_id are pure logic — tested directly, no
network. fetch_full_text's orchestration is mocked at the module boundary."""

from __future__ import annotations

import pytest

from rag.models import Paper
from rag.retrieval import fulltext

SAMPLE_TEI = """<?xml version="1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <body>
      <div><head>Introduction</head><p>We study things.</p></div>
      <div><head>Limitations</head><p>Our method is slow.</p><p>It also needs GPUs.</p></div>
      <div><p>Text with no heading.</p></div>
    </body>
  </text>
</TEI>"""


@pytest.fixture
def cache_dir(tmp_path, mocker):
    mocker.patch.object(
        type(fulltext.settings),
        "cache_path",
        new_callable=mocker.PropertyMock,
        return_value=tmp_path,
    )
    return tmp_path


def test_parse_sections_groups_by_heading() -> None:
    sections = fulltext.parse_sections(SAMPLE_TEI)

    assert sections["Introduction"] == "We study things."
    assert sections["Limitations"] == "Our method is slow. It also needs GPUs."
    assert sections["Untitled"] == "Text with no heading."


def test_extract_arxiv_id_from_arxiv_doi() -> None:
    paper = Paper(id="s2:x", title="t", doi="10.48550/arXiv.1706.03762")
    assert fulltext._extract_arxiv_id(paper) == "1706.03762"


def test_extract_arxiv_id_returns_none_for_non_arxiv_doi() -> None:
    paper = Paper(id="s2:x", title="t", doi="10.1000/xyz789")
    assert fulltext._extract_arxiv_id(paper) is None


def test_extract_arxiv_id_returns_none_when_no_doi() -> None:
    paper = Paper(id="s2:x", title="t")
    assert fulltext._extract_arxiv_id(paper) is None


def test_fetch_full_text_returns_none_when_no_oa_pdf_found(cache_dir, mocker) -> None:
    paper = Paper(id="s2:x", title="t")  # no doi -> not arXiv, no Unpaywall lookup possible
    mocker.patch.object(fulltext, "_fetch_pdf_bytes", return_value=None)

    assert fulltext.fetch_full_text(paper) is None


def test_fetch_full_text_uses_arxiv_when_doi_looks_like_arxiv(cache_dir, mocker) -> None:
    paper = Paper(id="s2:x", title="t", doi="10.48550/arXiv.1706.03762")
    fetch_arxiv = mocker.patch.object(fulltext, "fetch_arxiv_pdf", return_value=b"%PDF-fake")
    mocker.patch.object(fulltext, "fetch_tei", return_value=SAMPLE_TEI)

    sections = fulltext.fetch_full_text(paper)

    fetch_arxiv.assert_called_once_with("1706.03762")
    assert sections["Limitations"] == "Our method is slow. It also needs GPUs."


def test_fetch_full_text_caches_to_disk(cache_dir, mocker) -> None:
    paper = Paper(id="s2:cached", title="t", doi="10.48550/arXiv.1706.03762")
    fetch_arxiv = mocker.patch.object(fulltext, "fetch_arxiv_pdf", return_value=b"%PDF-fake")
    mocker.patch.object(fulltext, "fetch_tei", return_value=SAMPLE_TEI)

    fulltext.fetch_full_text(paper)
    fulltext.fetch_full_text(paper)

    fetch_arxiv.assert_called_once()  # second call hit the cache, not the network
