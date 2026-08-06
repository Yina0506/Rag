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

- [x] Full-text ingestion: `retrieval/fulltext.py` — arXiv (by DOI pattern
      `10.48550/arXiv.*`) or Unpaywall-by-DOI fetch → `retrieval/grobid_client.py`
      (factored out of `audit/grobid.py` so both phases share one GROBID HTTP call) →
      `parse_sections` (TEI `<div>`/`<head>` → `{heading: text}`). Disk-cached per paper id.
      **Code complete, not live-tested** — same GROBID-instance gap as Phase 4's PDF path.
- [x] `limitations/extract.py`:
  - [x] **Stated**: `extract_stated` — a heading regex (`Limitations`, `Future Work`,
        `Conclusion`, etc., optionally numbered) finds section starts; a generic
        "does this line look like *any* heading" check finds where the section ends (so it
        correctly stops at e.g. "References", not just another limitation-flavored heading);
        sentences inside become individual `Limitation` records.
  - [x] **Implicit** (the valuable part, per BAGELS): `extract_implicit` does both named
        mechanisms — (a) fetches each similar paper's own full text and borrows whatever
        `extract_stated` finds in *their* Limitations sections (the actual full-text upgrade
        this phase is about — reuses the same GROBID path, same live-test gap); (b) for
        similar papers published *later*, runs entailment(this paper's claim, later paper's
        abstract) and records a `CONTRADICTS` hit as an implicit limitation. (b) reuses
        `verify.entailment`, which **is** live-verified (Phase 3) — see live validation below.
  - [x] Normalize: each `Limitation` gets a `topic_embedding` via `retrieval.embed.embed_text`
        (behind the `ml` extra, same lazy pattern as Phase 1).
- [x] Dedupe near-identical limitations within a paper: `_dedupe` uses `difflib` text
      similarity (threshold 0.85) — deliberately not embedding-based, so dedup doesn't need
      the `ml` extra; embeddings are computed afterward, only for survivors.
- [x] `tests/` — 13 tests for `limitations/extract.py` (heading detection incl. correctly
      stopping at non-limitation headings, both implicit mechanisms, dedup, the
      underreporting gate) + 7 for `retrieval/fulltext.py` (section parsing, arXiv-id
      extraction, caching). No human-labeled sample yet — needs a real field corpus, which
      doesn't exist until Phase 6 builds one; OpenReview-comment gold set still open (below).

## Live validation (partial — GROBID-dependent pieces still unverified)

- `_find_similar_papers` against real S2: querying "Attention Is All You Need" correctly
  surfaced 3 real, topically-related papers and correctly excluded the paper itself once
  given its real S2 id (a self-titled near-duplicate DOES come back from a title search —
  the exclusion only works because `pipeline.extract_limitations` always passes a paper whose
  `.id` came from `sources.get_paper`, so it matches; confirmed both the failure mode with a
  synthetic id and the correct behavior with a real one).
- Contradiction detection (mechanism (b)) reuses Phase 3's already-live-verified entailer
  directly, so its correctness is inherited — but a live run surfaced a real, honest limit of
  the small local model: given a claim ("our proposed method achieves perfect accuracy") and
  contradicting evidence phrased indirectly ("the *original* method fails badly"), `qwen3:4b`
  graded it NEUTRAL — it didn't connect "the original method" to "our proposed method"
  without near-identical wording. Rephrasing the evidence to name "the proposed transformer
  model" directly then correctly produced CONTRADICTS (confidence 1.0). This is exactly the
  "expect it to misjudge hedged/nuanced claims" limitation Phase 3's notes already flagged —
  real thesis material (log entailer disagreements/misses), not a bug.
- Full-text fetch (arXiv/Unpaywall → GROBID) and mechanism (a) — **not** live-tested; no
  GROBID instance running. Do this together with Phase 4's PDF path once GROBID is up
  (`docker compose --profile phase5 up grobid`).

## Notes

- Ground truth idea (from BAGELS): use OpenReview reviewer comments as gold limitations for
  papers that have them — good for validating the extractor. **Still not built** — needs
  picking actual OpenReview papers in the field and hand-collecting their reviewer comments;
  not done here since it requires real, specific source data, not fabricable from memory.
- Passage-level evidence introduced here (`retrieval/fulltext.py`) is written to be reusable
  as an option for Phase 3's entailment (better grounding than abstract-only) but isn't
  wired in there yet — Phase 3 still defaults to abstract-level, as planned.
