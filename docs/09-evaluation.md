# 09 — Evaluation (cross-cutting)

Evaluation is what turns this from a demo into a thesis. Build it incrementally alongside
the phases; don't leave it to the end.

## Gold sets to build (you, mostly — see below)

1. **Retrieval/verification gold** (~100–200 triples): `(claim, paper, grade)` where grade ∈
   {SUPPORTS, WEAK, NEUTRAL, CONTRADICTS}. Source claims from real papers' cited sentences so
   you have a "known correct" citation, plus deliberately mismatched pairs. Hand-label.
2. **Existence gold**: real papers + fabricated ones + retracted ones (Phase 2 already seeds).
3. **NOT_FOUND set**: claims with *no* good supporting paper, to test the tool's willingness
   to abstain.
4. **Limitation gold** (Phase 5): papers with OpenReview reviewer comments as ground-truth
   limitations (BAGELS-style).
5. **Direction retrospective set** (Phase 6): a field corpus frozen at a cutoff year + the
   post-cutoff papers used to check follow-up.

## Metrics

- **Retrieval:** recall@k, MRR, context precision/recall (RAGAS).
- **Verification:** graded accuracy / macro-F1 over the 4 grades; abstention correctness on
  the NOT_FOUND set.
- **The money chart:** hallucination rate + mismatch rate of **naive LLM ("give me a
  citation for X")** vs **this system**. Prior work already shows naive prompting <10%
  citation accuracy — reproduce that baseline and show your delta.
- **Existence gate:** false-accept rate on fabricated papers (target 0).
- **Limitations:** precision/recall vs OpenReview gold.
- **Directions:** follow-up rate of top-k discovered directions in the post-cutoff window;
  expert plausibility ratings (small panel).

## Baselines to implement

- B0: naive LLM citation generation (the thing we're beating).
- B1: retrieval-only (no entailment) — shows entailment's added value.
- B2: NLI-model entailment vs LLM-as-entailer — internal comparison.

## Notes

- RAGAS for the RAG-style metrics; custom scripts for the graded/abstention/retrospective
  parts (RAGAS won't cover those).
- Keep every eval reproducible: fixed seeds, cached API responses, versioned gold files in
  `data/eval/`.
