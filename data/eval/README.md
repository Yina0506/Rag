# Eval gold sets

Kept out of `.gitignore`'s `data/` rule (see `docs/09-evaluation.md`) so gold
files are versioned. Populate per phase — don't fabricate labels, hand-label
from real papers.

- `test_claims.jsonl` — Phase 1 seed: ~10 claims for retrieval sanity-checking
  (`notebooks/01_retrieval_sanity.ipynb`). One JSON object per line:
  `{"claim": str, "source_paper_doi": str | null, "notes": str | null}`
- Phase 3+: extend with `(claim, paper, grade)` triples — real cited pairs plus
  deliberately mismatched ones — for the verification gold set.
- Phase 2: fabricated + retracted paper examples for the existence-gate gold set.
- Phase 5: OpenReview-comment-derived limitation gold (BAGELS-style).
- Phase 6: field corpus frozen at a cutoff year, for retrospective validation.
