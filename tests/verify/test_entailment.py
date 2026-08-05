"""Phase 3. The money-maker: graded accuracy + willingness to abstain (NOT_FOUND)."""

import pytest


@pytest.mark.xfail(reason="Phase 3: implement rag.verify.entailment", strict=False)
def test_entailer_never_invents_content_beyond_evidence() -> None:
    from rag.verify.entailment import entail

    entail("claim not in evidence", "unrelated evidence text")


@pytest.mark.xfail(reason="Phase 3: implement rag.verify.entailment", strict=False)
def test_entailer_abstains_when_no_support() -> None:
    from rag.models import Grade
    from rag.verify.entailment import entail

    grade, _confidence = entail("claim", "irrelevant evidence")
    assert grade == Grade.NOT_FOUND
