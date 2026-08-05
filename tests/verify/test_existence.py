"""Phase 2. The gate is load-bearing: a fabricated paper must always be rejected."""

import pytest


@pytest.mark.xfail(reason="Phase 2: implement rag.verify.existence", strict=False)
def test_fabricated_paper_is_rejected() -> None:
    from rag.models import ExistenceStatus, Paper
    from rag.verify.existence import existence_verdict

    fake = Paper(id="fake:1", doi="10.9999/does-not-exist", title="Fabricated Paper Title")
    assert existence_verdict(fake) == ExistenceStatus.NOT_FOUND


@pytest.mark.xfail(reason="Phase 2: implement rag.verify.existence", strict=False)
def test_retracted_paper_is_flagged() -> None:
    from rag.verify.existence import is_retracted

    is_retracted(None)  # replace with a known-retracted fixture DOI
