# Phase 6 — Research-Direction Discovery (Pillar C)

**Goal:** aggregate limitations across a whole field, cluster recurring gaps into candidate
research directions, and cross-reference the citation graph to mark each direction as still
open vs. already addressed. This is the most novel part.

**Entry criteria:** Phase 5 produces `Limitation` records over a field corpus.

**Exit criteria:** for a chosen field, output a ranked list of `Direction`s, each with:
frequency (how many papers raise it), representative statement, member limitations, and a
`still_open` flag with the papers that (partly) solved it. Retrospective validation (below)
shows the method surfaces directions that were later actually worked on.

## The three moves (this is the contribution)

1. **Aggregate** — pool all `Limitation`s across the field corpus.
2. **Cluster** — embed + **HDBSCAN**; each dense cluster = a candidate direction. Frequency
   = cluster size (weighted by distinct papers). A gap raised by 30 papers >> one raised once.
3. **Check openness** — for each cluster, search for *later* papers that address it; use the
   citation graph (do later papers citing the gap-raisers claim to solve it?) + entailment
   ("does this later paper's contribution resolve this limitation?"). Mark `still_open`.

## Tasks

- [x] `directions/cluster.py`:
  - [x] `cluster_limitations` — embeds each `Limitation` (reusing Phase 5's
        `topic_embedding` when already set, computing it otherwise) and runs HDBSCAN with no
        preset k; the noise label (-1) is dropped since a limitation nothing else resembles
        isn't a "direction" by this method's own frequency-weighted definition.
  - [x] `label_cluster` — LLM (via `rag.llm.get_llm()`) summarizes a cluster into one
        direction statement, prompted to never invent beyond the member limitations' own
        text. **Live-verified**: 3 differently-worded English-only-evaluation limitations
        correctly collapsed into one accurate, grounded sentence.
  - [x] `build_directions` — ranks by frequency = **distinct paper count** per cluster (not
        raw limitation count — a single paper can land >1 limitation in the same cluster),
        matching "a gap raised by 30 papers >> one raised once."
- [x] `directions/openness.py`:
  - [x] `find_later_papers` — unions two sources per docs' "citation graph... + topically
        similar": (1) `sources.get_citing_papers` (new S2 endpoint, added this phase) on
        each gap-raising paper, and (2) a topical `search_papers` on the direction's own
        label — a later paper solving a problem doesn't always cite every paper that
        mentioned it as future work. Both filtered to strictly after the latest known
        gap-raiser year.
  - [x] `check_openness` — frames "does this resolve the gap?" as an entailment question
        (does the later paper's abstract SUPPORT/WEAK-support the claim that it addresses
        the direction's gap statement?), reusing Phase 3's entailer — never assumes a paper
        solves something just because it's later or topically similar.
- [x] `pipeline.discover_directions(field_query, corpus_size=20)` — corpus build (direct S2
      search on the field query; the bounded-corpus-with-cutoff-year strategy from
      `02-data-sources.md` isn't its own implemented step yet) → extract (Phase 5, per paper)
      → cluster → openness → ranked `Direction`s. `corpus_size` defaults small (20) since
      each paper can trigger several S2 searches + LLM entailment calls in Phase 5's
      implicit-extraction path — expensive to run at real field-corpus scale (hundreds of
      papers) without batching/caching discipline this phase didn't need to solve yet.
- [ ] UI: field explorer view — not built. `01-architecture.md` scopes all UI work to
      Streamlit, explicitly gated to "don't build the UI before Phase 3" with no phase
      re-committing to exactly when after that; deferred along with the rest of the UI.

## Live validation (partial — same shape as Phases 4-5's gaps)

- `get_citing_papers` (new S2 `/citations` endpoint) against the real API: correctly returned
  real citing papers for "Attention Is All You Need" (hit a transient 429 mid-session from
  cumulative live-testing load, not a bug — confirmed via a direct request, then succeeded on
  retry).
- `label_cluster` against real `qwen3:4b`: three independently-worded "English-only
  evaluation" limitation statements correctly collapsed into one accurate, grounded direction
  sentence — fast too (~30s with a warm model, no `/no_think` issues since Phase 3's fix).
- **Not live-tested**: `cluster_limitations` (needs the `cluster` extra for HDBSCAN — not
  installed) and `check_openness`'s entailment loop end-to-end (would need a real corpus, and
  Phase 5's implicit-extraction path is itself still partly GROBID-gated) and the full
  `pipeline.discover_directions` run (would compound Phase 3-5's live-call costs across an
  entire corpus — expensive to run just to prove the wiring, which unit tests already cover).

## Evaluation — retrospective validation (see `09-evaluation.md`)

- Build the field corpus with a **cutoff year** (e.g. only papers ≤2021). Run discovery.
- Check whether the top directions were actually pursued in 2022–2025 (via later papers /
  their citations). A good method's "open directions from 2021" should have measurable
  follow-up. This gives a *quantitative* signal without needing to judge "good idea" directly.
- Also: small expert panel rates a sample of directions for plausibility/usefulness.
- **Not built yet** — needs the real field corpus (Chinese-poetry/LLM-generation evaluation,
  per `docs/PROGRESS.md`'s field definition) that no phase has actually assembled at scale.

## Notes

- Openness detection is the least-explored, most defensible novelty — spend effort there.
- Be honest in the thesis: "promising" is subjective; retrospective follow-up is a proxy,
  not proof. State it.
- All six build phases (`03`-`08`) are now implemented and unit-tested (98 tests passing,
  zero xfails). What's left everywhere is the same short list: `uv sync --extra ml`/`cluster`
  for real embeddings/reranking/clustering, a running GROBID instance for full-text/PDF
  ingestion, and assembling the actual field corpus — see `docs/PROGRESS.md` "Next up."
