# Phase 3 — Entailment / Graded Support (Pillar A core)

**Goal:** decide whether a real paper *actually supports* the claim. This is the heart of
the project — it's what fixes the "real paper, wrong claim" mismatch. Output is graded.

**Entry criteria:** Phases 1–2 done (real, existing candidates in hand).

**Exit criteria:** `verify_claim(claim)` returns full `Verdict`s with grade + evidence
passage + justification + confidence. On the gold set (see `09-evaluation.md`), graded
accuracy beats a naive "ask the LLM if it's relevant" baseline. Tool correctly returns
`NOT_FOUND` when no candidate genuinely supports the claim.

## Tasks

- [ ] `verify/entailment.py`:
  - [ ] `entail(claim, evidence) -> {SUPPORTS, WEAK, NEUTRAL, CONTRADICTS}` +confidence.
        Two implementations behind one interface:
    - [ ] **LLM-as-entailer**: structured-output prompt, reasons ONLY over `evidence` text.
    - [ ] **NLI model**: DeBERTa-v3 NLI (map entailment→SUPPORTS, contradiction→CONTRADICTS,
          neutral→NEUTRAL; threshold a WEAK band).
  - [ ] Evidence selection: abstract-level for now (passage-level deferred to Phase 5).
  - [ ] `justify(claim, evidence, grade) -> str` — 1–2 sentence rationale, quoting the
        supporting span. Never invents beyond `evidence`.
- [ ] Aggregate into `pipeline.verify_claim`: retrieve → existence gate → entail → sort →
      return graded verdicts; emit explicit `NOT_FOUND` if best grade < WEAK.
- [ ] Guardrail test: assert the entailer never emits a claim/number not present in evidence.
- [ ] `notebooks/03_entailment_vs_baseline.ipynb` — LLM-entailer vs NLI vs naive baseline.

## Notes

- **Local small-model reality (M2 8GB):** the LLM-as-entailer runs on `qwen3:4b`. Expect it
  to handle clear SUPPORTS/CONTRADICTS well but misjudge hedged/nuanced scientific claims
  more than a big model would. That's acceptable — the graded method + eval is the point.
  The DeBERTa NLI model is small too and runs locally; comparing the two is still valid and
  useful thesis material. Load the LLM only after embedding/retrieval is done (memory).

- **This is the thesis money-maker.** Invest evaluation effort here (gold set in Phase-eval).
- Scientific claims are nuanced; expect NLI-on-general-text to misjudge hedged claims. Log
  disagreements between the two entailers — they're thesis material.
- Keep the "willing to say NOT_FOUND" behavior first-class and tested; it's the whole point.
