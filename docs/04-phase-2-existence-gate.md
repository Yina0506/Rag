# Phase 2 — Existence Gate (Pillar A)

**Goal:** guarantee zero fabricated citations by construction. Every paper that leaves the
pipeline must resolve to a real DOI/ID and be checked against retractions.

**Entry criteria:** Phase 1 retrieval works.

**Exit criteria:** `existence_check(paper)` returns a hard verdict; a deliberately fake
paper (fabricated title+DOI) is always rejected; retracted papers are flagged. Gate is wired
so nothing bypasses it before presentation.

## Tasks

- [ ] `verify/existence.py`:
  - [ ] `resolve_doi(paper) -> bool` via Crossref (and S2 id fallback).
  - [ ] `is_retracted(paper) -> bool` via Retraction Watch / Crossref retraction metadata.
  - [ ] `existence_verdict(paper) -> {EXISTS, NOT_FOUND, RETRACTED}`.
- [ ] Wire gate into `pipeline.py`: candidates failing existence are dropped/flagged, never
      silently returned.
- [ ] Fuzzy-match guard: when a candidate came from an LLM-suggested title (Phase 4 case),
      match title+authors+year against Crossref before trusting it.
- [ ] `tests/` — inject a fabricated paper → assert rejected; inject a known retracted DOI →
      assert flagged.
- [ ] Extend `data/eval/` with 5 fabricated and 3 retracted examples for regression.

## Notes

- This is short but load-bearing. The whole trust story rests on this gate being
  non-bypassable. Make it a single choke point in `pipeline.py`.
- Cache Crossref lookups; they're the hot path.
