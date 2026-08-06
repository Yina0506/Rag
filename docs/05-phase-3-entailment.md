# Phase 3 — Entailment / Graded Support (Pillar A core)

**Goal:** decide whether a real paper *actually supports* the claim. This is the heart of
the project — it's what fixes the "real paper, wrong claim" mismatch. Output is graded.

**Entry criteria:** Phases 1–2 done (real, existing candidates in hand).

**Exit criteria:** `verify_claim(claim)` returns full `Verdict`s with grade + evidence
passage + justification + confidence. On the gold set (see `09-evaluation.md`), graded
accuracy beats a naive "ask the LLM if it's relevant" baseline. Tool correctly returns
`NOT_FOUND` when no candidate genuinely supports the claim.

## Tasks

- [x] `verify/entailment.py`:
  - [x] `entail(claim, evidence) -> {SUPPORTS, WEAK, NEUTRAL, CONTRADICTS}` +confidence.
        Two implementations behind one interface (`settings.entailment_backend`):
    - [x] **LLM-as-entailer**: structured-output prompt (`GRADE:`/`CONFIDENCE:`/
          `JUSTIFICATION:`), reasons ONLY over `evidence` text. Runs on `qwen3:4b` via
          `rag.llm.get_llm()`. **Live-verified against the real model** (not just mocked) on
          three hand-written cases — SUPPORTS, NEUTRAL (off-topic evidence), CONTRADICTS
          (evidence directly contradicts the claim) — all three graded correctly with
          sensible confidence and a justification quoting the evidence.
    - [x] **NLI model**: `cross-encoder/nli-deberta-v3-base` (a DeBERTa-v3 NLI cross-encoder,
          reuses the `sentence-transformers` dependency already needed for reranking — no new
          `ml`-extra dependency). Maps entailment→SUPPORTS/WEAK (0.7 threshold),
          contradiction→CONTRADICTS, neutral→NEUTRAL. **Live-verified 2026-08-06** (SUPPORTS
          and CONTRADICTS cases both correctly graded with high confidence) — and this run
          caught a real bug: `CrossEncoder.predict` returns raw un-normalized logits (e.g.
          4.6, -4.9), not probabilities. Using them directly as "confidence" produced values
          >1, and the 0.7 grading threshold was being compared against logits it was never
          calibrated for. Fixed with softmax normalization in `nli_entail`; mocked unit tests
          updated to use realistic logit-scale values instead of pre-normalized ones.
  - [x] Evidence selection: abstract-level (`candidate.paper.abstract`); passage-level
        deferred to Phase 5 as planned.
  - [x] `justify(claim, evidence, grade) -> str` — for the LLM backend this is produced in
        the SAME completion as the grade (one model call, not two); `justify` recomputes via
        the configured backend rather than trusting a stale `grade` argument.
- [x] Aggregated into `pipeline.verify_claim`: retrieve → existence gate → entail → sort →
      graded `Verdict`s; the top verdict's grade is overridden to `NOT_FOUND` when it doesn't
      clear WEAK, with a justification naming the closest candidate's actual grade — the tool
      explicitly refuses rather than silently ranking a bad candidate first.
- [x] Guardrail tests: the LLM prompt is asserted to contain the "reason only over evidence /
      never use outside knowledge" instruction; malformed model output falls back to NEUTRAL
      with 0.0 confidence rather than silently defaulting toward SUPPORTS. Full guardrail
      validation (does qwen3:4b actually never hallucinate in practice) is an eval-time
      question, not something a mocked unit test can prove — see `09-evaluation.md`.
- [ ] `notebooks/03_entailment_vs_baseline.ipynb` — not built yet; needs the same live-corpus
      setup as Phase 1's deferred notebook run plus a naive-LLM-citation baseline (`09-evaluation.md`
      B0) to compare against. Do this alongside Phase 1/2's deferred live validation.

## Notes

- **Local small-model reality (M2 8GB), confirmed in practice:** `qwen3:4b` graded all three
  live test cases correctly. The real cost turned out to be **cold-load latency, not
  reasoning quality or "thinking mode"** — Ollama unloads an idle model after ~5 minutes, and
  reloading it from disk took ~2-3 minutes on this machine each time. `llm.py`'s `OllamaClient`
  now appends Qwen3's native `/no_think` directive by default (its `"think": false` request
  field is silently ignored by qwen3:4b on both `/api/generate` and `/api/chat` — tested
  directly) and the HTTP timeout was raised to 240s to survive a cold load. A warm model
  responds in single-digit seconds; plan corpus/eval runs around that, e.g. keep a request
  warming the model periodically during a batch run rather than letting it go idle.
- **Real bug caught during this phase, now fixed:** `_run_entailer`'s original dispatch was a
  module-level `dict` built once at import time (`{"llm": llm_entail, "nli": nli_entail}`),
  which captured the *original* function objects — patching `entailment.llm_entail` in a test
  silently didn't take effect, so a "mocked" test suite actually hit the real Ollama server
  and took 7 minutes instead of under a second. Fixed by dispatching on the backend name each
  call instead of through a frozen dict. Worth remembering for Phase 5/6, which will add more
  swappable-backend dispatch tables.
- **This is the thesis money-maker.** Invest evaluation effort here (gold set in Phase-eval) —
  still needs a real gold set; `data/eval/` doesn't have entailment triples yet.
- Scientific claims are nuanced; expect NLI-on-general-text to misjudge hedged claims. Log
  disagreements between the two entailers once both are live-tested — they're thesis material.
- The "willing to say NOT_FOUND" behavior is first-class and tested (unit level); still needs
  eval-level validation on real claims once the corpus is live.
