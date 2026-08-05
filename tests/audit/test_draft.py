"""Phase 4. Fixture draft with planted good/bad/fake/retracted citations."""

import pytest


@pytest.mark.xfail(reason="Phase 4: implement rag.audit.draft", strict=False)
def test_audit_classifies_each_planted_citation() -> None:
    from rag.audit.draft import audit

    audit("tests/fixtures/draft_with_planted_citations.bib")
