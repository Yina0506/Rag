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

- [ ] `config.py` — load env, model names, cache dir.
- [ ] `models.py` — implement `Paper`, `Claim`, `Candidate` dataclasses per `01-architecture.md`.
- [ ] `retrieval/sources.py` — S2 client (`search_papers`, `get_paper`), OpenAlex fallback.
      Shared HTTP client w/ retry, on-disk cache, rate limiter, polite User-Agent.
- [ ] `retrieval/embed.py` — SPECTER2 embeddings for papers; BGE-M3 for claim text.
- [ ] `retrieval/index.py` — Qdrant wrapper (embedded mode ok): create collection, upsert
      papers, vector search with metadata filters (year, venue).
- [ ] `retrieval/rerank.py` — BGE-reranker-v2-m3 cross-encoder over (claim, abstract) pairs.
- [ ] `pipeline.py` — `retrieve_candidates(claim, k)`: API search → embed → index/search →
      rerank → top-k `Candidate`s.
- [ ] `tests/` — unit tests for sources (mocked HTTP), index roundtrip, rerank ordering.
- [ ] `notebooks/01_retrieval_sanity.ipynb` — run 10 test claims, eyeball results.
- [ ] Seed `data/eval/test_claims.jsonl` with 10 claims (reuse in every later phase).

## Notes for the implementing session

- Prefer embedded Qdrant to avoid docker dependency this early.
- SPECTER2 loads via HuggingFace `allenai/specter2`; cache the model locally.
- Keep the API layer and the index layer independent so we can swap either.
- Don't build the UI yet.
