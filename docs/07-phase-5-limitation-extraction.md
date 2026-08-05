# Phase 5 — Limitation & Future-Work Extraction (Pillar B)

**Goal:** from a paper (and a field corpus), extract both *stated* limitations/future-work
and *implicit* ones (shortcomings a paper underreports but that similar papers or later work
reveal). Grounds Pillar C.

**Entry criteria:** Phase 3 done; a bounded field corpus can be built (see `02-data-sources.md`).
This phase also introduces **full-text / passage-level** retrieval, upgrading Phase 3's
abstract-only evidence.

**Exit criteria:** for a set of papers, produce structured `Limitation` records (stated +
implicit) that a human judges as accurate on a sample. Full-text passage retrieval works.

## Tasks

- [ ] Full-text ingestion: arXiv/PMC/Unpaywall fetch → GROBID → sectioned text. Cache.
- [ ] `limitations/extract.py`:
  - [ ] **Stated**: locate Limitations / Future Work / Conclusion sections; extract spans.
  - [ ] **Implicit** (the valuable part, per BAGELS): for a paper lacking/underreporting
        limitations, retrieve *similar* papers (same method/dataset) and surface limitations
        they raise that plausibly apply; and detect claims later papers contradict (reuse
        entailment: does a newer paper CONTRADICT this paper's claim?).
  - [ ] Normalize each limitation to a short canonical statement + topic embedding.
- [ ] Dedupe near-identical limitations within a paper.
- [ ] `tests/` + a small human-labeled sample for spot-checking.

## Notes

- Ground truth idea (from BAGELS): use OpenReview reviewer comments as gold limitations for
  papers that have them — good for validating the extractor.
- Passage-level evidence introduced here should be back-ported as an *option* to Phase 3's
  entailment (better grounding), but keep abstract-level as the fast default.
