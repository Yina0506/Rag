# Phase 4 — Draft Audit / Mode B (Pillar A applied)

**Goal:** take a real draft (PDF/LaTeX/.bib) and audit every (claim, citation) pair —
flagging mismatches, unsupported claims, fabricated refs, and retractions. This is the mode
that directly serves the original pain point.

**Entry criteria:** Phase 3 entailment works.

**Exit criteria:** feed in a document with known-good and known-bad citations → get a report
that correctly classifies each. Multi-step audit runs reliably over a full draft.

## Tasks

- [ ] `audit/draft.py`:
  - [ ] Ingest: GROBID for PDF → TEI; direct parse for `.bib`/`.tex`.
  - [ ] Pair extraction: associate each in-text claim with its cited reference(s).
  - [ ] For each pair: resolve the cited paper (existence gate) → fetch its abstract →
        run entailment(claim, cited-paper) → grade.
  - [ ] Report: per-pair ✅/⚠️/❌/🚫 + suggested better citation (reuse `verify_claim`) when ❌.
- [ ] Consider **LangGraph** here: retrieve → existence → entail → suggest is a natural
      multi-node graph; introduce it now, not earlier.
- [ ] Output formats: JSON report + human-readable Markdown summary.
- [ ] `tests/` — a fixture draft with planted good/bad/fake/retracted citations.

## Notes

- Claim–citation association is the fiddly part (a sentence may cite several papers; a
  citation may span several sentences). Start with sentence-level heuristics; note failures.
- This phase turns the tool from "toy" into "actually useful to a thesis writer."
