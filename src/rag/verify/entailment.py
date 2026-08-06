"""Claim vs. evidence -> graded verdict. The thesis money-maker (docs/05-phase-3).

Two implementations behind one interface, selected by `settings.entailment_backend`:
- `llm_entail`: structured-output prompt over `rag.llm.get_llm()` (qwen3:4b via
  Ollama by default), reasons ONLY over `evidence` text.
- `nli_entail`: a DeBERTa-v3 NLI cross-encoder (`ml` optional-dependency group,
  reuses the sentence-transformers dependency already needed for reranking).

`entail`/`justify` never return NOT_FOUND — that grade is a pipeline-level
concept (see `pipeline.verify_claim`): "no candidate cleared WEAK", not
something a single (claim, evidence) judgment can express on its own.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

from rag.config import settings
from rag.llm import get_llm
from rag.models import Grade

_GRADE_PATTERN = re.compile(r"GRADE:\s*(SUPPORTS|WEAK|NEUTRAL|CONTRADICTS)", re.IGNORECASE)
_CONFIDENCE_PATTERN = re.compile(r"CONFIDENCE:\s*([0-9.]+)")
_JUSTIFICATION_PATTERN = re.compile(r"JUSTIFICATION:\s*(.+)", re.IGNORECASE | re.DOTALL)

_ENTAIL_PROMPT = """You are grading whether a piece of evidence supports a claim. \
Reason ONLY about the evidence text below. Never use outside knowledge and never state \
anything that isn't directly present in the evidence.

CLAIM: {claim}

EVIDENCE: {evidence}

Grade the evidence against the claim using exactly one of:
- SUPPORTS: the evidence clearly and directly supports the claim.
- WEAK: the evidence is related and lends some support, but doesn't fully establish the claim.
- NEUTRAL: the evidence is on-topic but neither supports nor contradicts the claim.
- CONTRADICTS: the evidence directly contradicts the claim.

Respond in EXACTLY this format and nothing else:
GRADE: <one of SUPPORTS, WEAK, NEUTRAL, CONTRADICTS>
CONFIDENCE: <a number between 0.0 and 1.0>
JUSTIFICATION: <1-2 sentences, quoting the relevant span of the evidence. State nothing \
that is not present in the evidence above.>
"""


def llm_entail(claim: str, evidence: str) -> tuple[Grade, float, str]:
    """Returns (grade, confidence, justification) from a single completion —
    cheaper than two round-trips to a local model that's already the slowest
    part of the pipeline."""
    response = get_llm().complete(_ENTAIL_PROMPT.format(claim=claim, evidence=evidence))
    return _parse_entail_response(response)


def _parse_entail_response(response: str) -> tuple[Grade, float, str]:
    grade_match = _GRADE_PATTERN.search(response)
    if not grade_match:
        # The model didn't follow the format — don't guess a grade. Treat it
        # as the weakest non-contradictory signal rather than silently
        # defaulting to something that looks like support.
        return Grade.NEUTRAL, 0.0, "Entailer response could not be parsed; treated as NEUTRAL."

    grade = Grade(grade_match.group(1).upper())
    confidence_match = _CONFIDENCE_PATTERN.search(response)
    confidence = max(0.0, min(1.0, float(confidence_match.group(1)))) if confidence_match else 0.5
    justification_match = _JUSTIFICATION_PATTERN.search(response)
    justification = (
        justification_match.group(1).strip() if justification_match else response.strip()
    )
    return grade, confidence, justification


@lru_cache(maxsize=1)
def _nli_model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.nli_model)


def nli_entail(claim: str, evidence: str) -> tuple[Grade, float, str]:
    """`cross-encoder/nli-deberta-v3-base` (and the other sentence-transformers
    NLI cross-encoders) return 3 scores in the fixed order
    [contradiction, entailment, neutral] per the model card.

    **Live-caught bug**: `CrossEncoder.predict` returns raw un-normalized
    logits (e.g. 4.6, -4.9), not probabilities — using them directly as
    "confidence" produced nonsense values >1, and the 0.7 SUPPORTS/WEAK
    threshold in `_nli_scores_to_grade` was being compared against logits it
    was never calibrated for. Softmax-normalized here so confidence is a
    real probability and the threshold means what it says.
    """
    raw_scores = [float(s) for s in _nli_model().predict([(evidence, claim)])[0]]
    exp_scores = [math.exp(s) for s in raw_scores]
    total = sum(exp_scores)
    contradiction, entailment, neutral = (s / total for s in exp_scores)

    grade = _nli_scores_to_grade(entailment, contradiction, neutral)
    confidence = max(entailment, contradiction, neutral)
    justification = (
        f"NLI scores — entailment: {entailment:.2f}, contradiction: {contradiction:.2f}, "
        f"neutral: {neutral:.2f}."
    )
    return grade, confidence, justification


def _nli_scores_to_grade(entailment: float, contradiction: float, neutral: float) -> Grade:
    if contradiction > entailment and contradiction > neutral:
        return Grade.CONTRADICTS
    if entailment > neutral:
        return Grade.SUPPORTS if entailment >= 0.7 else Grade.WEAK
    return Grade.NEUTRAL


def _run_entailer(claim: str, evidence: str) -> tuple[Grade, float, str]:
    """Dispatches by name each call rather than through a dict of function
    references captured at import time — a frozen dict would keep pointing at
    the original `llm_entail`/`nli_entail` even after a test (or a caller)
    monkeypatches the module attribute, silently bypassing the mock and
    hitting the real backend instead."""
    backend = settings.entailment_backend
    if backend == "llm":
        return llm_entail(claim, evidence)
    if backend == "nli":
        return nli_entail(claim, evidence)
    raise ValueError(f"Unknown entailment backend: {backend}")


def entail(claim: str, evidence: str) -> tuple[Grade, float]:
    """Returns (grade, confidence) using the configured backend. Never invents
    content beyond `evidence` — enforced by prompt design for the LLM backend;
    the NLI backend has no generative component to hallucinate with."""
    grade, confidence, _justification = _run_entailer(claim, evidence)
    return grade, confidence


def justify(claim: str, evidence: str, grade: Grade) -> str:
    """1-2 sentence rationale quoting the supporting span. `grade` is accepted
    for interface stability (docs/01-architecture.md) but not used to alter
    the result — recomputing via the configured backend keeps this function
    correct even if a caller passes a stale grade. Calling `entail` then
    `justify` back-to-back costs two model calls; `pipeline.verify_claim`
    avoids that by calling `_run_entailer` directly instead of going through
    this public pair.
    """
    _grade, _confidence, justification = _run_entailer(claim, evidence)
    return justification
