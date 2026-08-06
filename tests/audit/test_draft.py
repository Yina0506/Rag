"""Fixture draft (tests/fixtures/sample_draft.{tex,bib}) with planted
good/fabricated/retracted/mismatched citations. Parsing tests run against the
real fixture files (no mocking needed — pure text logic); existence/
entailment are mocked since they'd otherwise hit real Crossref/S2/Ollama."""

from __future__ import annotations

from pathlib import Path

from rag.audit import draft
from rag.models import ExistenceStatus, Grade, Paper

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_bibtex_extracts_all_fields() -> None:
    entries = draft.parse_bibtex((FIXTURES / "sample_draft.bib").read_text())

    assert set(entries) == {"realgood2023", "fabricated2024", "retracted2020", "mismatch2022"}
    real = entries["realgood2023"]
    assert real.title == "Evaluating Neural Poetry Generation in Chinese"
    assert real.doi == "10.1000/realgood2023"
    assert real.year == 2023
    assert real.authors == ["Author, A.", "Author, B."]

    fabricated = entries["fabricated2024"]
    assert fabricated.doi is None


def test_parse_tex_citations_splits_sentences_and_strips_cite_commands() -> None:
    pairs = draft.parse_tex_citations((FIXTURES / "sample_draft.tex").read_text())

    keys = [key for _claim, key in pairs]
    assert keys.count("realgood2023") == 2  # once alone, once in the combined-citation sentence
    assert "fabricated2024" in keys
    claim_for_realgood = next(c for c, k in pairs if k == "realgood2023" and "tonal" in c)
    assert r"\cite" not in claim_for_realgood
    assert claim_for_realgood.endswith(".")


def test_parse_tex_citations_ignores_sentences_without_cite() -> None:
    text = "This sentence has no citation at all. Neither does this one."
    assert draft.parse_tex_citations(text) == []


def test_with_abstract_falls_back_to_title_search_when_doi_lookup_misses(mocker) -> None:
    """Regression (found live): a real paper can have multiple valid DOIs
    across registration systems, so a Crossref-returned DOI isn't guaranteed
    to be the one S2 indexes it under. When the direct DOI lookup comes back
    empty, search by title instead of giving up."""
    paper = Paper(
        id="doi:10.1/mismatched-registry-doi",
        doi="10.1/mismatched-registry-doi",
        title="Attention Is All You Need",
    )
    mocker.patch("rag.retrieval.sources.get_paper", return_value=None)
    found_by_title = Paper(
        id="s2:real", title="Attention Is All You Need", abstract="The dominant sequence..."
    )
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[found_by_title])

    resolved = draft._with_abstract(paper)

    assert resolved.abstract == "The dominant sequence..."


def test_with_abstract_rejects_unrelated_title_search_result(mocker) -> None:
    paper = Paper(id="doi:10.1/x", doi="10.1/x", title="Attention Is All You Need")
    mocker.patch("rag.retrieval.sources.get_paper", return_value=None)
    unrelated = Paper(id="s2:other", title="A Totally Different Paper", abstract="unrelated")
    mocker.patch("rag.retrieval.sources.search_papers", return_value=[unrelated])

    resolved = draft._with_abstract(paper)

    assert resolved.abstract is None


def test_audit_pair_missing_key_is_fabricated() -> None:
    finding = draft.audit_pair("some claim", "not_a_real_key", bib_entries={})

    assert finding.existence == ExistenceStatus.NOT_FOUND
    assert finding.symbol == "🚫"
    assert finding.verdict is None


def test_audit_pair_supports_grade_maps_to_check_symbol(mocker) -> None:
    entry = Paper(id="bib:x", doi="10.1000/x", title="Real Paper")
    mocker.patch.object(
        draft, "resolve_bib_paper", return_value=(ExistenceStatus.EXISTS, entry)
    )
    mocker.patch(
        "rag.verify.entailment._run_entailer", return_value=(Grade.SUPPORTS, 0.9, "supports it")
    )

    finding = draft.audit_pair("claim text", "x", bib_entries={"x": entry})

    assert finding.symbol == "✅"
    assert finding.verdict is not None
    assert finding.verdict.grade == Grade.SUPPORTS
    assert finding.suggested_citation is None


def test_audit_pair_contradicts_grade_suggests_alternative(mocker) -> None:
    entry = Paper(id="bib:x", doi="10.1000/x", title="Wrong Paper")
    alternative = Paper(id="s2:better", title="A Better Paper", abstract="directly on point")
    mocker.patch.object(
        draft, "resolve_bib_paper", return_value=(ExistenceStatus.EXISTS, entry)
    )
    mocker.patch(
        "rag.verify.entailment._run_entailer",
        return_value=(Grade.CONTRADICTS, 0.8, "contradicts the claim"),
    )
    from rag.models import Claim, Verdict

    better_verdict = Verdict(
        claim=Claim(text="claim text"),
        paper=alternative,
        grade=Grade.SUPPORTS,
        confidence=0.9,
        justification="j",
    )
    mocker.patch("rag.pipeline.verify_claim", return_value=[better_verdict])

    finding = draft.audit_pair("claim text", "x", bib_entries={"x": entry})

    assert finding.symbol == "❌"
    assert finding.suggested_citation == alternative


def test_audit_pair_retracted_is_hard_stop(mocker) -> None:
    entry = Paper(id="bib:x", doi="10.1000/x", title="Retracted Paper")
    mocker.patch.object(
        draft, "resolve_bib_paper", return_value=(ExistenceStatus.RETRACTED, entry)
    )

    finding = draft.audit_pair("claim text", "x", bib_entries={"x": entry})

    assert finding.symbol == "🚫"
    assert finding.existence == ExistenceStatus.RETRACTED
    assert finding.verdict is None


def test_full_audit_classifies_every_planted_citation(mocker) -> None:
    """The end-to-end exit criteria from docs/06: feed a document with
    known-good and known-bad citations, get correctly classified results."""

    def fake_resolve(entry: Paper):
        if entry.id == "bib:realgood2023":
            return ExistenceStatus.EXISTS, entry.model_copy(
                update={"abstract": "We enforce tonal constraints via constrained decoding."}
            )
        if entry.id == "bib:fabricated2024":
            return ExistenceStatus.NOT_FOUND, entry
        if entry.id == "bib:retracted2020":
            return ExistenceStatus.RETRACTED, entry
        if entry.id == "bib:mismatch2022":
            return ExistenceStatus.EXISTS, entry.model_copy(
                update={"abstract": "We study protein folding with deep learning."}
            )
        raise AssertionError(f"unexpected entry {entry.id}")

    def fake_entailer(claim: str, evidence: str):
        if "tonal" in evidence:
            return (Grade.SUPPORTS, 0.95, "supports")
        if "protein folding" in evidence:
            return (Grade.CONTRADICTS, 0.7, "unrelated/contradicts")
        raise AssertionError("entailer should not be called for gated-out pairs")

    mocker.patch.object(draft, "resolve_bib_paper", side_effect=fake_resolve)
    mocker.patch("rag.verify.entailment._run_entailer", side_effect=fake_entailer)
    mocker.patch("rag.pipeline.verify_claim", return_value=[])

    result = draft.audit(
        str(FIXTURES / "sample_draft.tex"), bib_path=str(FIXTURES / "sample_draft.bib")
    )

    symbols_by_key: dict[str, set[str]] = {}
    for finding in result["findings"]:
        symbols_by_key.setdefault(finding["citation_key"], set()).add(finding["symbol"])

    assert symbols_by_key["realgood2023"] == {"✅"}
    assert symbols_by_key["fabricated2024"] == {"🚫"}
    assert symbols_by_key["retracted2020"] == {"🚫"}
    assert symbols_by_key["mismatch2022"] == {"❌"}
    assert "# Draft Audit Report" in result["markdown"]


def test_bib_only_draft_runs_existence_only(mocker) -> None:
    mocker.patch.object(
        draft,
        "resolve_bib_paper",
        side_effect=lambda entry: (ExistenceStatus.NOT_FOUND, entry),
    )

    result = draft.audit(str(FIXTURES / "sample_draft.bib"))

    assert len(result["findings"]) == 4
    assert all(f["symbol"] == "🚫" for f in result["findings"])
