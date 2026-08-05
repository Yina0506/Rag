"""Phase 6. A gap raised by many papers should outrank one raised once."""

import pytest


@pytest.mark.xfail(reason="Phase 6: implement rag.directions.cluster", strict=False)
def test_frequent_limitation_ranks_above_rare_one() -> None:
    from rag.directions.cluster import build_directions

    build_directions([])
