# Eval gold sets

This directory is versioned (`.gitignore` only excludes `data/cache/`,
`data/corpus/`, `data/qdrant/` — see `docs/09-evaluation.md`). Populate per
phase — don't fabricate labels, hand-label from real papers.

- `test_claims.jsonl` — Phase 1 seed: ~10 claims for retrieval sanity-checking
  (`notebooks/01_retrieval_sanity.ipynb`). One JSON object per line:
  `{"claim": str, "source_paper_doi": str | null, "notes": str | null}`
- `existence_gold.jsonl` — Phase 2: 5 synthetic fabricated-paper fixtures
  (safe to invent — they're deliberately fake) + 3 `RETRACTED` placeholders
  still marked `"doi": "TODO"`. Fill those from
  https://retractionwatch.com or Crossref (`filter=update-type:retraction`)
  before relying on them for a real regression run — not fabricated here
  since inventing a specific retraction claim would itself be a fabrication.
  Schema: `{"doi": str | null, "title": str, "id": str | null, "expected":
  "NOT_FOUND" | "RETRACTED" | "EXISTS", "notes": str}`.
- Phase 3+: extend with `(claim, paper, grade)` triples — real cited pairs plus
  deliberately mismatched ones — for the verification gold set.
- Phase 5: OpenReview-comment-derived limitation gold (BAGELS-style).
- Phase 6: field corpus frozen at a cutoff year, for retrospective validation.
