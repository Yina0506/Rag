"""Aggregate + HDBSCAN cluster limitations into candidate directions
(docs/08-phase-6-direction-discovery.md). This is the most novel part.

Each dense cluster = a candidate direction; frequency = cluster size weighted
by distinct papers. Cluster labels are LLM-summarized but grounded ONLY on
member limitations — same "never invent beyond retrieved text" rule as elsewhere.
"""

from __future__ import annotations

from rag.models import Direction, Limitation


def cluster_limitations(limitations: list[Limitation]) -> list[list[Limitation]]:
    """Embed + HDBSCAN. No preset k."""
    raise NotImplementedError("Phase 6")


def label_cluster(cluster: list[Limitation]) -> str:
    """LLM summarizes a cluster into one direction statement."""
    raise NotImplementedError("Phase 6")


def build_directions(limitations: list[Limitation]) -> list[Direction]:
    raise NotImplementedError("Phase 6")
