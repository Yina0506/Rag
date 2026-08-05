"""Claim vs. evidence -> graded verdict. The thesis money-maker (docs/05-phase-3).

Two implementations behind one interface — compare them in eval:
- LLM-as-entailer: structured-output prompt, reasons ONLY over `evidence` text.
- NLI model: DeBERTa-v3 NLI, mapped to the same grade scale.

Must be willing to return NOT_FOUND / a grade below WEAK — abstaining is a
first-class, tested behavior, not a failure mode.
"""

from __future__ import annotations

from rag.models import Grade


def entail(claim: str, evidence: str) -> tuple[Grade, float]:
    """Returns (grade, confidence). Never invents content beyond `evidence`."""
    raise NotImplementedError("Phase 3")


def justify(claim: str, evidence: str, grade: Grade) -> str:
    """1-2 sentence rationale quoting the supporting span. Grounded only in evidence."""
    raise NotImplementedError("Phase 3")
