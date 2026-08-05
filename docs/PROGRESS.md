# PROGRESS — living status tracker

> Update this every session. It's the first thing the next session reads.

## Current phase: **Phase 2 — Existence Gate** (code complete, live validation pending)

## Field definition for Pillars B/C
**The intersection: evaluation of LLM / neural poetry generation, with emphasis on Chinese
poetry.** Not the broad label "AI in cultural studies" (too broad — would drown the
limitation clustering). The corpus sits at the overlap of:
- NLP / text-generation *evaluation* (the truest home — this is a benchmarking study),
- computational creativity (machine generation of poetry/art; venue e.g. ICCC),
- computational literary studies / digital humanities (the Chinese-poetry / cultural-form side),
- multilingual / Chinese NLP (classical Chinese, tonal & metrical constraints).
Build the field corpus from this intersection so clustered limitations form coherent
directions. (Matches Julius's own thesis area -> he can sanity-check discovered directions.)

## Scope decisions
- **English-language papers only** (v1). Simplifies embeddings, corpus queries, and eval.
  [!] **Stated thesis limitation:** some primary Chinese-poetry-generation work is published
  in Chinese-language venues, so an English-only corpus under-represents part of the field.
  Declare this explicitly in the thesis; don't let a reviewer surface it.
- Verification is graded (SUPPORTS/WEAK/NEUTRAL/CONTRADICTS/NOT_FOUND).
- Existence gate is a hard, non-bypassable choke point.
- Abstract-level evidence first; passage-level from Phase 5.
- Tool must be able to answer "no supporting paper found" (tested).

## LLM decision
- **Hardware:** Apple M2, 8GB unified memory, no discrete GPU. Constrains local model size.
- **Local, free, no API, no cloud** — this is a *practice* project; the full RAG setup
  matters more than raw model quality. Small model is fine.
- **Default: `qwen3:4b` via Ollama** (~2.5GB at Q4) — reasons well enough to exercise every
  pipeline stage; leaves headroom for macOS + embedding models. Qwen chosen over Llama for
  Chinese subject-matter handling (poetry terms, author names) even in English papers.
- **Fallback: `qwen3:1.7b`** if 4b is sluggish once embedding models are also in memory.
- **Do NOT pull 8b** — ~6GB fights macOS on 8GB and swaps to disk.
- **[!] Run stages sequentially, not simultaneously.** 8GB is shared across the LLM and the
  embedding/reranker models. Embed+index the corpus first (load→run→unload), THEN load the
  LLM for entailment/extraction. Batch + cache to disk between stages. This staged approach
  is the difference between "works" and "swaps and crawls" on 8GB.
- **Provider stays swappable via `llm.py`.** Entailment accuracy with a 4b model will be
  lower than with a frontier model — that's fine, the *method* is the contribution. Report
  the small local model as the working system; note the layer is model-swappable, and
  optionally do ONE comparison run against a stronger model later without other changes.
- **No paid API, no cloud rental** in v1. (If ever needed for a single batch/eval later,
  the wrapper makes it a drop-in — but not part of the plan.)

## Phase 0 tasks (scaffold — do these first)
- [x] Create repo skeleton per README layout (`src/rag/`, `tests/`, `data/`, `notebooks/`).
- [x] `pyproject.toml` with deps: httpx, pydantic, qdrant-client, python-dotenv, pytest
      (core, installed) + sentence-transformers/transformers/torch/hdbscan/ragas/streamlit
      as `uv` optional-dependency groups (`ml`, `cluster`, `eval`, `ui` — installed lazily
      per phase via `uv sync --extra <name>`, per the "install lazily if heavy" note).
- [x] `.env.example` with `S2_API_KEY`, `CONTACT_EMAIL`, `LLM_PROVIDER`, `*_API_KEY`.
- [x] `.gitignore` (data/ subdirs, .env, __pycache__, model caches).
- [x] `src/rag/config.py` (pydantic-settings: env/`.env` loaded, cache dir, all model names).
- [ ] Install Ollama + pull a Qwen model; smoke-test through `llm.py` stub. **[! blocker below]**
- [x] `git init`, first commit.

## Additional scaffold beyond the original Phase 0 list
- [x] `uv` as the package/env manager: `pyproject.toml` + `uv.lock` committed;
      `uv sync` installs core+dev in ~1s (no torch download yet).
- [x] Full `src/rag/` module boundaries stubbed per `01-architecture.md` (retrieval/,
      verify/, audit/, limitations/, directions/, pipeline.py) — each raises
      `NotImplementedError` with a docstring pointing at the phase that implements it.
- [x] `models.py` fully implemented (Paper/Claim/Candidate/Verdict/Limitation/Direction
      as pydantic models, per the architecture doc's data contracts).
- [x] `llm.py` has a working `OllamaClient` (httpx call to `/api/generate`); OpenAI/Anthropic
      clients are typed stubs behind the same interface, per "never hardcode a vendor."
- [x] `tests/` mirrors `src/rag/`; real tests for `models.py`/`config.py` pass, unimplemented
      modules have `xfail`-marked tests so the suite documents what Phase 1–6 must satisfy.
- [x] Docker deployment: `Dockerfile` (`uv`-based multi-stage-ish build) + `docker-compose.yml`
      running **Qdrant** (`server` mode) + the app; `grobid` service behind a `phase5` profile.
      Ollama stays native on the host (Metal acceleration) — compose points at
      `host.docker.internal:11434`. Validated with `docker compose config`.
- [x] `Makefile` (`make setup|test|lint|fmt|run|docker-up|docker-down`).
- [x] Planning docs moved into `docs/` to match this file's own repo-layout description.

## Phase 1 tasks (retrieval backbone — see `docs/03-phase-1-retrieval.md` for detail)
- [x] `rag/http.py` — shared retry/cache/rate-limited HTTP client (new module, not in the
      original architecture doc list but needed from day 1; Phase 2's Crossref client will
      reuse it too).
- [x] `retrieval/sources.py` — S2 `search_papers`/`get_paper` + OpenAlex fallback, English
      filtered (ASCII-ratio heuristic on the abstract for now).
- [x] `retrieval/embed.py` — SPECTER2 (paper) + BGE-M3 (text) embeddings, lazy-loaded,
      behind the `ml` optional-dependency group.
- [x] `retrieval/index.py` — Qdrant wrapper: `ensure_collection`/`upsert_papers`/`search`
      with year/venue filters. Verified against qdrant-client 1.19's live API (`:memory:`
      client) before writing, not just assumed.
- [x] `retrieval/rerank.py` — BGE-reranker-v2-m3 cross-encoder, behind `ml`.
- [x] `pipeline.retrieve_candidates` — wires search → index → vector search → rerank.
      `pipeline.verify_claim` is a documented-provisional alias for it (Phase 2/3 change its
      return type to graded `Verdict`s).
- [x] Tests: `uv run pytest` → **20 passed, 7 xfailed** (xfails are all Phase 2–6 work now —
      Phase 1's own xfails from Phase 0 are gone). Everything mocked, no network/ML deps
      needed to run the suite. `ruff check` and `mypy src` both clean.
- [ ] **Not done yet:** running the notebook / hitting live APIs / seeding 10 real eval
      claims. All three need `uv sync --extra ml` (multi-GB torch + model download) and,
      ideally, a real `S2_API_KEY`. Deliberately not done without asking first — see
      "Next up" below.

## Phase 2 tasks (existence gate — see `docs/04-phase-2-existence-gate.md` for detail)
- [x] `verify/existence.py` — `resolve_doi` (Crossref + S2-id fallback), `is_retracted`
      (Crossref `update-to`/`is-retracted-by`), `existence_verdict`, and
      `fuzzy_match_existence` (title+author+year fuzzy match via Crossref bibliographic
      search — wired for Phase 4's draft-audit mode, not called anywhere yet).
- [x] Gate wired into `pipeline.retrieve_candidates` as the single choke point:
      `NOT_FOUND` candidates dropped, `RETRACTED` ones flagged (`paper.retracted = True`)
      rather than silently dropped. `verify_claim` inherits this for free since it's still
      an alias for `retrieve_candidates`.
- [x] Tests: `uv run pytest` → **31 passed, 5 xfailed** (Phase 2's own xfails are gone; only
      Phase 3–6 remain). Fabricated-paper rejection, both retraction-detection paths, the
      DOI-less S2 fallback, fuzzy-match accept/reject, and the pipeline gate itself
      (drop vs. flag, no in-place mutation) are all covered — mocked, no real network.
      `ruff check` / `mypy src` clean.
- [x] `data/eval/existence_gold.jsonl` seeded: 5 synthetic fabricated fixtures (safe to
      invent) + 3 `RETRACTED` rows left as `"doi": "TODO"` — deliberately not filled with
      invented DOIs; needs a real retracted paper looked up before it's useful for a live
      regression run.

## Done log
- 2026-08-05: Phase 0 scaffold built. `uv run pytest` → 5 passed, 10 xfailed. `ruff check`
  and `mypy src` clean.
- 2026-08-05: Phase 1 retrieval backbone implemented. Unit-test-level exit bar met; live
  exit criteria (10 real claims -> ≥5 relevant papers each) still open — deferred, see below.
- 2026-08-05: Phase 2 existence gate implemented and wired into the pipeline as the sole
  choke point (see above). Same live-validation gap as Phase 1: unit tests all mock
  `cached_get`, so this hasn't hit real Crossref yet.

## Next up
- Phase 3 (`docs/05-phase-3-entailment.md`) needs Ollama running locally — still not
  installed on this machine. Either install Ollama + pull `qwen3:4b` now, or do Phase 3's
  NLI-model entailer path first (DeBERTa, no Ollama needed) and add the LLM-as-entailer once
  Ollama's in place.
- Still deferred from Phase 1: live validation (`uv sync --extra ml`, a real S2 API key,
  running `notebooks/01_retrieval_sanity.ipynb` against real APIs, filling in
  `data/eval/test_claims.jsonl` and the 3 `RETRACTED` rows in `existence_gold.jsonl` with
  real data). None of this blocks writing more code, only blocks *proving* Phases 1–2 work
  end-to-end — worth doing before the thesis write-up leans on either exit criteria.
- Still blocked on: Ollama install, S2 API key, `CONTACT_EMAIL`.

## Decisions made
- Stack locked per `01-architecture.md` (Qdrant embedded, SQLite, SPECTER2+BGE-M3, graded
  entailment, Streamlit UI, LangGraph only from Phase 4).
- Field, English-only scope, and Qwen-default LLM — recorded above.

## Blockers / waiting on Julius
- [ ] Semantic Scholar API key in `.env` (request form -> key by email; `x-api-key` header)
- [ ] Contact email for OpenAlex/Crossref polite pools
- [ ] Ollama installed + `qwen3:4b` pulled (fallback `qwen3:1.7b`) — no API key needed
- [x] Docker installed (v29.2.1) — `docker-compose.yml` runs Qdrant now; GROBID is
      behind the `phase5` compose profile, not needed until then.

## Parking lot (ideas, don't act yet)
- Multilingual / Chinese-language corpus — deferred; would directly address the stated
  English-only limitation if the project extends past v1.
- Browser extension / real-time — out of scope.
