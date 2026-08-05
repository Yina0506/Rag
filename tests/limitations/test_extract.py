"""Phase 5. Spot-check against a small human-labeled sample."""

import pytest


@pytest.mark.xfail(reason="Phase 5: implement rag.limitations.extract", strict=False)
def test_extract_finds_stated_limitations_section(sample_paper) -> None:
    from rag.limitations.extract import extract_stated

    extract_stated(sample_paper, full_text="... Limitations: our method assumes ...")
