"""Citation-graph "still open?" check (docs/08-phase-6-direction-discovery.md).

Per cluster: gather later papers (year > cluster papers, topically similar or
citing the gap-raisers) -> entailment check "does this later paper's
contribution resolve this limitation?" -> set still_open + solving_papers.
Least-explored, most defensible novelty in the thesis — spend effort here.
"""

from __future__ import annotations

from rag.models import Direction


def find_later_papers(direction: Direction) -> list[str]:
    raise NotImplementedError("Phase 6")


def check_openness(direction: Direction) -> Direction:
    """Returns `direction` with `still_open` and `solving_papers` populated."""
    raise NotImplementedError("Phase 6")
