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

- [ ] `directions/cluster.py` — embed limitations, HDBSCAN, label clusters (LLM summarizes a
      cluster into one direction statement, grounded only on member limitations), rank by freq.
- [ ] `directions/openness.py` — per cluster: gather later papers (year > cluster papers,
      topically similar / citing) → entailment check "resolves this gap?" → set `still_open`
      + `solving_papers`.
- [ ] `pipeline.discover_directions(field)` — corpus build → extract (Phase 5) → cluster →
      openness → ranked `Direction`s.
- [ ] UI: field explorer view (list directions, drill into member papers + limitations).

## Evaluation — retrospective validation (see `09-evaluation.md`)

- Build the field corpus with a **cutoff year** (e.g. only papers ≤2021). Run discovery.
- Check whether the top directions were actually pursued in 2022–2025 (via later papers /
  their citations). A good method's "open directions from 2021" should have measurable
  follow-up. This gives a *quantitative* signal without needing to judge "good idea" directly.
- Also: small expert panel rates a sample of directions for plausibility/usefulness.

## Notes

- Openness detection is the least-explored, most defensible novelty — spend effort there.
- Be honest in the thesis: "promising" is subjective; retrospective follow-up is a proxy,
  not proof. State it.
