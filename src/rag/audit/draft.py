"""Draft audit / Mode B (docs/06-phase-4-draft-audit.md).

Ingest a real draft (PDF/.bib/.tex), associate each in-text claim with its
cited reference(s), and run existence + entailment per pair. This is the mode
that directly serves the original thesis-writing pain point.
"""

from __future__ import annotations


def ingest(path: str) -> str:
    """GROBID for PDF -> TEI; direct parse for .bib/.tex. Returns extracted text."""
    raise NotImplementedError("Phase 4")


def extract_claim_citation_pairs(text: str) -> list[tuple[str, str]]:
    """Sentence-level heuristics first; a sentence may cite several papers."""
    raise NotImplementedError("Phase 4")


def audit(path: str) -> dict:
    """Per-pair report: resolve cited paper -> existence gate -> entailment -> grade."""
    raise NotImplementedError("Phase 4")
