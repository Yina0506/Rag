# Phase 1 — Retrieval Backbone (Pillar A foundation)

**Goal:** given a claim string, return real, ranked candidate papers from live scholarly
APIs + a local vector index. No verification yet — just "can we surface relevant real
papers." Proves the retrieval half works.

**Entry criteria:** Phase 0 scaffold done (`pyproject.toml`, `src/rag/`, `.env` with
`S2_API_KEY` + `CONTACT_EMAIL`).

**Exit criteria:** `verify_claim(claim)` (retrieval-only stub) returns ≥5 relevant real
papers for 10 hand-picked test claims; results cached; a notebook shows precision looks
sane by eye.

## Tasks

- [x] `config.py` — load env, model names, cache dir.
- [x] `models.py` — implement `Paper`, `Claim`, `Candidate` dataclasses per `01-architecture.md`.
- [x] `retrieval/sources.py` — S2 client (`search_papers`, `get_paper`), OpenAlex fallback.
      Shared HTTP client w/ retry, on-disk cache, rate limiter, polite User-Agent
      (`rag/http.py`, new — not in the original module list but needed from day 1 per
      `02-data-sources.md`; Phase 2's Crossref client will reuse it).
- [x] `retrieval/embed.py` — SPECTER2 embeddings for papers; BGE-M3 for claim text.
      Implemented behind the `ml` optional-dependency group (lazy-loaded, not yet
      exercised against real weights — see "Still open" below).
- [x] `retrieval/index.py` — Qdrant wrapper (embedded mode ok): create collection, upsert
      papers, vector search with metadata filters (year, venue).
- [x] `retrieval/rerank.py` — BGE-reranker-v2-m3 cross-encoder over (claim, abstract) pairs.
      Same `ml`-extra caveat as embed.py.
- [x] `pipeline.py` — `retrieve_candidates(claim, k)`: API search → embed → index/search →
      rerank → top-k `Candidate`s. `verify_claim` is currently an alias for this (documented
      as provisional — Phase 2/3 change its return type to graded `Verdict`s).
- [x] `tests/` — unit tests for sources (mocked HTTP), index roundtrip (in-memory Qdrant),
      rerank ordering (mocked cross-encoder), plus `test_http.py` and `test_pipeline.py`
      for the wiring. All mocked — no network, no ML deps needed to run `uv run pytest`.
- [ ] `notebooks/01_retrieval_sanity.ipynb` — notebook exists and is wired to
      `retrieve_candidates`, but has NOT been run yet: needs `uv sync --extra ml`
      (downloads torch + SPECTER2/BGE-M3/reranker weights, multi-GB) and a live S2/OpenAlex
      run. Deferred pending user go-ahead given the 8GB-machine/bandwidth cost.
- [ ] Seed `data/eval/test_claims.jsonl` with 10 real claims. File exists with the agreed
      JSONL schema and one placeholder row — deliberately not fabricated from memory (that's
      exactly the failure mode this project fixes). Fill in from real papers once retrieval
      has been run live, or hand-pick from known papers in the field.

## Still open (code complete, not yet validated live)

- Exit criteria ("`verify_claim` returns ≥5 relevant real papers for 10 hand-picked test
  claims") needs: (1) `uv sync --extra ml` to pull torch/sentence-transformers/the three
  model checkpoints, (2) an `.env` with a working `S2_API_KEY`/`CONTACT_EMAIL` (or run
  anonymous-pool, slower), (3) the 10 real seed claims above, (4) actually running the
  notebook. None of this needed unit tests to pass, but exit criteria isn't met until it's
  done — see `docs/PROGRESS.md`.
- `allenai/specter2` is loaded here as a plain `sentence-transformers` model; true SPECTER2
  behavior needs its proximity adapter via the `adapters` package. Flagged in `embed.py` —
  revisit if paper-similarity quality looks off once real eval is possible.

## Notes for the implementing session

- Prefer embedded Qdrant to avoid docker dependency this early.
- SPECTER2 loads via HuggingFace `allenai/specter2`; cache the model locally.
- Keep the API layer and the index layer independent so we can swap either.
- Don't build the UI yet.
