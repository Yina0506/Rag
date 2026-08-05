# Phase 2 — Existence Gate (Pillar A)

**Goal:** guarantee zero fabricated citations by construction. Every paper that leaves the
pipeline must resolve to a real DOI/ID and be checked against retractions.

**Entry criteria:** Phase 1 retrieval works.

**Exit criteria:** `existence_check(paper)` returns a hard verdict; a deliberately fake
paper (fabricated title+DOI) is always rejected; retracted papers are flagged. Gate is wired
so nothing bypasses it before presentation.

## Tasks

- [x] `verify/existence.py`:
  - [x] `resolve_doi(paper) -> bool` via Crossref (and S2 id fallback).
  - [x] `is_retracted(paper) -> bool` via Crossref retraction metadata (`update-to` type
        `retraction` and the `is-retracted-by` relation). DOI-less papers can't be checked
        this way and are never flagged retracted — documented gap, not silent.
  - [x] `existence_verdict(paper) -> {EXISTS, NOT_FOUND, RETRACTED}`.
- [x] Wire gate into `pipeline.py`: `retrieve_candidates` applies `_apply_existence_gate`
      after reranking — `NOT_FOUND` candidates are dropped, `RETRACTED` ones are kept but
      flagged (`paper.retracted = True`) rather than silently vanishing. This is the single
      choke point; nothing calls the retrieval stages directly and skips it.
- [x] `fuzzy_match_existence(title, authors, year)` — queries Crossref's bibliographic
      search, accepts a hit only if `difflib.SequenceMatcher` title similarity ≥ 0.85 (and
      year within 1 if given). Wired for Phase 4 to call once draft audit exists; not yet
      called anywhere since Phase 4 isn't built.
- [x] `tests/` — `tests/verify/test_existence.py` (fabricated paper rejected, real DOI
      resolves, retraction via both `update-to` and `relation`, DOI-less S2 fallback both
      ways, non-404 errors propagate instead of being swallowed, fuzzy match accept/reject)
      + `tests/test_pipeline.py` (gate drops NOT_FOUND, flags RETRACTED without mutating the
      original Paper). All mocked at the `cached_get` boundary — no real network.
- [x] `data/eval/existence_gold.jsonl` — 5 synthetic fabricated-paper fixtures (safe to
      invent, deliberately fake) + 3 `RETRACTED` placeholders still marked `"doi": "TODO"`.
      Real retracted DOIs deliberately NOT fabricated from memory — get them from
      retractionwatch.com or Crossref before using this file for a live regression run.

## Notes

- This is short but load-bearing. The whole trust story rests on this gate being
  non-bypassable. Make it a single choke point in `pipeline.py`.
- Cache Crossref lookups; they're the hot path.
- Exit criteria is met at the unit-test level (fabricated paper always rejected, retraction
  detection logic covered, gate wired as the sole path). Not yet validated against real
  Crossref responses over the network — same live-validation gap as Phase 1, see
  `docs/PROGRESS.md`.
