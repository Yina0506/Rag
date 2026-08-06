# Phase 4 — Draft Audit / Mode B (Pillar A applied)

**Goal:** take a real draft (PDF/LaTeX/.bib) and audit every (claim, citation) pair —
flagging mismatches, unsupported claims, fabricated refs, and retractions. This is the mode
that directly serves the original pain point.

**Entry criteria:** Phase 3 entailment works.

**Exit criteria:** feed in a document with known-good and known-bad citations → get a report
that correctly classifies each. Multi-step audit runs reliably over a full draft.

## Tasks

- [x] `audit/draft.py`:
  - [x] Ingest: direct parse for `.bib`/`.tex` (via `bibtexparser` + a sentence-level `\cite`
        regex). GROBID PDF→TEI split into a separate `audit/grobid.py` module — **code
        complete, not live-tested** (no GROBID instance running; see docs/PROGRESS.md).
  - [x] Pair extraction: `parse_tex_citations` splits into sentences, strips `\cite`-family
        commands, and pairs the cleaned sentence with each citation key found in it (a
        sentence citing two papers yields two independent pairs).
  - [x] For each pair: `resolve_bib_paper` (existence gate: direct DOI resolution, or
        `fuzzy_match_existence` for DOI-less entries — reusing Phase 2 exactly as planned)
        → `_with_abstract` (fetch evidence) → `_run_entailer` → grade.
  - [x] Report: per-pair ✅/⚠️/❌/🚫 (see `audit/draft.py`'s module docstring for the exact
        grade→symbol mapping) + suggested better citation (reuse `pipeline.verify_claim`)
        when ❌. `render_markdown_report` + JSON (`AuditFinding.model_dump()`) both implemented.
- [x] LangGraph: **not introduced.** Considered per this doc's suggestion, but the actual
      control flow (resolve → existence → entail → suggest) is a straight linear pipeline
      over independent pairs — same shape Phase 3's `verify_claim` already handles with plain
      functions. No branching/cyclic logic here that would justify the framework weight.
      Documented as a deliberate decision, not an oversight — revisit if a later phase's
      audit logic actually needs multi-step planning.
- [x] Output formats: JSON (`result["findings"]`) + Markdown (`result["markdown"]`) both
      returned from `audit()`.
- [x] `tests/` — `tests/fixtures/sample_draft.{tex,bib}` plants all four cases (real DOI +
      SUPPORTS, DOI-less fabricated title, retracted DOI, real-but-off-topic mismatch);
      `tests/audit/test_draft.py` has 11 tests covering parsing (real, unmocked) and the
      existence/entailment-dependent logic (mocked). `uv run pytest` → 57 passed, 2 xfailed.

## Live validation — done, not deferred like Phases 1-3

Once the Semantic Scholar API key arrived mid-session, this phase got a real end-to-end live
run (not just mocked units) — the first time the retrieval + existence-gate machinery from
Phases 1-2 was exercised against real APIs too:
- `retrieval.sources.search_papers` against the real S2 API: correctly surfaced the real
  "Attention Is All You Need" among other real, relevant results.
- `verify.existence.fuzzy_match_existence` against real Crossref: resolved "Attention Is All
  You Need" to a real DOI with the correct 8-author list; correctly returned `None` for a
  fabricated title.
- Full `audit_pair` end-to-end on (a) a real paper with an on-topic claim → `✅ SUPPORTS` with
  a justification quoting the real abstract, and (b) a fabricated citation → `🚫 NOT_FOUND`.

**Real bug caught by this live run, now fixed:** `sources.get_paper` raised an unhandled
`HTTPStatusError` on a 404 instead of returning `None` as its own signature promised — this
crashed `audit_pair` outright the first time a Crossref-resolved DOI wasn't the one S2
indexes a paper under (common: a paper can have an arXiv preprint DOI and a separate
proceedings DOI). Fixed in `sources.get_paper` (404 → `None`, matches its documented
contract) with a regression test.

**Real gap caught and fixed, not just worked around:** even after that fix, DOI-only abstract
lookup produced an honest-but-useless `NEUTRAL` (no evidence, so no support) for a paper that
unambiguously exists and is on-topic — the DOI Crossref returned simply wasn't the one S2
indexes it under. Added a title-search fallback in `_with_abstract`; re-running the same live
case then correctly produced `✅ SUPPORTS` with the real abstract as evidence.

## Notes

- Claim–citation association is the fiddly part (a sentence may cite several papers; a
  citation may span several sentences). Sentence-level heuristics are in place; known
  limitations documented in `parse_tex_citations`'s docstring (abbreviations like "e.g."
  can split a sentence early; a citation spanning multiple sentences only attaches to the
  one it's textually inside).
- This phase turns the tool from "toy" into "actually useful to a thesis writer" — and,
  as of the live run above, it's the first phase actually proven against real data end to end.
