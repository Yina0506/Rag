"""Shared fixtures. No network in unit tests — mock all external HTTP here."""

from __future__ import annotations

import pytest

from rag.models import Paper


@pytest.fixture
def sample_paper() -> Paper:
    return Paper(
        id="s2:123",
        doi="10.1000/example",
        title="Evaluating Neural Poetry Generation",
        abstract="We study evaluation methods for LLM-generated Chinese poetry.",
        year=2024,
        venue="ICCC",
        authors=["A. Author"],
    )
