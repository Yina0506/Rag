# 00 — Project Overview

## Motivation

While writing a thesis, using LLMs to find supporting references produced frequent
**fabricated papers** and **semantic mismatches** (real paper, wrong claim). This project
fixes that at the source: citations come from retrieval + verification, never from LLM
recall. It then extends the same backbone to help *find* research directions by mining
what the literature says is unsolved.

## The three pillars

| # | Pillar | Input | Output | Attacks |
|---|--------|-------|--------|---------|
| A | Citation verification | a claim, or (claim, citation) pairs | verified citations + entailment grade + supporting passage | fabricated & mismatched citations |
| B | Limitation extraction | a paper / set of papers in a field | structured list of stated + implicit limitations | limitations are underreported/scattered |
| C | Direction discovery | a field (corpus of papers) | ranked open research directions, with "still open?" status | no tool aggregates gaps across a field & checks if they're solved |

Pillars build on each other: A gives the entailment + retrieval backbone; B reuses
retrieval to harvest limitation text; C aggregates B's output and reuses A's citation-graph
logic to check whether a gap is still open.

## Scope decisions (locked)

- **Verification is graded, not binary.** Support levels: `SUPPORTS` / `WEAK` / `NEUTRAL` /
  `CONTRADICTS` / `NOT_FOUND`.
- **Existence is a hard, non-bypassable gate.** Any paper that doesn't resolve to a real
  DOI/ID is flagged and never presented as a citation.
- **Abstract-level first, passage-level later.** Start with abstracts (easy, covers most);
  add full-text passage grounding as an upgrade.
- **The tool must be willing to say "no supporting paper found."** This is the opposite of
  the LLM behavior we're fixing and must be tested explicitly.
- **"Direction quality" has no ground truth.** Evaluate C mainly via *retrospective
  validation* (see `09-evaluation.md`), not by claiming to predict good ideas.

## Non-goals

- Not writing prose for the user / not a "write my related-work section" tool.
- Not a reference manager (export to BibTeX/CSL, but Zotero already manages libraries).
- Not real-time / not a browser extension (at least not in thesis scope).
- Not multilingual at first — English corpus initially; multilingual embeddings chosen so
  it *can* extend, but non-English eval is out of scope for v1.

## How the pillars map to build phases

- Phase 0 — scaffold (repo, env, deps)
- Phase 1 — retrieval backbone (Pillar A foundation)
- Phase 2 — existence gate (Pillar A)
- Phase 3 — entailment / graded support (Pillar A core)
- Phase 4 — draft audit / Mode B (Pillar A applied)
- Phase 5 — limitation extraction (Pillar B)
- Phase 6 — direction discovery (Pillar C)
- Cross-cutting — evaluation harness (grows from Phase 1 on)

A working, defensible tool exists after Phase 3. Phases 4–6 are the novel thesis
contribution. Do them in order; each phase's doc lists entry criteria.
