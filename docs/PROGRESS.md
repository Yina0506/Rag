# PROGRESS — living status tracker

> Update this every session. It's the first thing the next session reads.

## Current phase: **Phase 4 — Draft Audit** (done, live-verified end-to-end; PDF/GROBID path untested)

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
- [x] Install Ollama + pull a Qwen model; smoke-test through `llm.py` stub. Installed via
      `brew install ollama`, running as a background service (`brew services start ollama`).
      Pulled `qwen3:4b` (2.5GB, the documented default above). `get_llm().complete(...)`
      round-trips correctly through `OllamaClient`.
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

## Phase 3 tasks (entailment — see `docs/05-phase-3-entailment.md` for detail)
- [x] `verify/entailment.py` — `llm_entail` (qwen3:4b via Ollama, structured `GRADE:`/
      `CONFIDENCE:`/`JUSTIFICATION:` prompt) and `nli_entail` (`cross-encoder/nli-deberta-v3-base`,
      reuses the `ml` extra's sentence-transformers dep, no new dependency) behind one
      `entail`/`justify` interface, selected by `settings.entailment_backend`.
- [x] **Live-verified the LLM backend against the real model** (not just mocked) — SUPPORTS,
      NEUTRAL, and CONTRADICTS cases all graded correctly with sensible confidence and a
      justification quoting the evidence. NLI backend still code-only, needs `ml` extra.
- [x] `pipeline.verify_claim` now does the real retrieve → gate → entail → sort → grade flow
      (no longer an alias for `retrieve_candidates`); overrides the top verdict to
      `NOT_FOUND` when nothing clears WEAK.
- [x] Two real things found and fixed while building this:
  - Ollama's `"think": false` field is silently ignored by `qwen3:4b` — switched to
    appending its native `/no_think` directive, and raised the HTTP timeout to 240s after
    measuring a ~2-3 minute cold-model-load cost (Ollama unloads after ~5min idle). This
    was the actual bottleneck, not reasoning quality or "thinking mode" itself.
  - `_run_entailer` originally dispatched through a dict of function references captured at
    import time, which silently defeated test mocks and made the "mocked" test suite
    actually call the real Ollama server (7 minutes instead of under a second). Fixed to
    dispatch by name each call.
- [x] Tests: `uv run pytest` → **43 passed, 3 xfailed** (Phase 3's own xfails gone; only
      Phase 4–6 remain). `ruff check` / `mypy src` clean.
- [ ] `notebooks/03_entailment_vs_baseline.ipynb` not built — same live-corpus dependency as
      Phase 1/2's deferred validation, plus a naive-LLM-citation baseline to compare against.

## Phase 4 tasks (draft audit — see `docs/06-phase-4-draft-audit.md` for detail)
- [x] `audit/draft.py` — `.bib`/`.tex` ingestion (`bibtexparser` + sentence-level `\cite`
      regex), `resolve_bib_paper` (reuses Phase 2's existence gate exactly as planned),
      `_with_abstract` (evidence fetch, with a title-search fallback — see bug below),
      `audit_pair`/`audit` orchestration, JSON + Markdown report output.
- [x] `audit/grobid.py` — PDF→TEI via GROBID, split into its own module since it's the
      heavy/optional path. **Code complete, not live-tested** (no GROBID instance running).
- [x] LangGraph: deliberately **not** introduced — the per-pair flow is linear, no
      branching/cyclic logic to justify it. Documented as a decision, not skipped work.
- [x] `tests/fixtures/sample_draft.{tex,bib}` plants all four cases (good/fabricated/
      retracted/mismatched); `tests/audit/test_draft.py` — 11 tests.
- [x] **Live-validated end-to-end** — the real S2 API key arrived mid-session. Ran the whole
      chain against real APIs for the first time: S2 search, Crossref fuzzy-match existence,
      abstract fetch, and Ollama entailment all correctly handled a real paper ("Attention Is
      All You Need" → ✅ SUPPORTS with a justification quoting the real abstract) and a
      fabricated one (→ 🚫 NOT_FOUND). This also live-validates chunks of Phases 1 and 2 that
      were previously mock-only — see their docs for what's now confirmed vs. still open.
- [x] Two real bugs found via that live run, both fixed with regression tests:
  - `sources.get_paper` raised on a 404 instead of returning `None` per its own signature —
    crashed the very first time a Crossref-resolved DOI wasn't the one S2 indexes under.
  - DOI-only abstract lookup silently produced an honest-but-useless NEUTRAL for a paper that
    unambiguously exists (S2 didn't have that specific DOI indexed) — added a title-search
    fallback in `_with_abstract`; the same live case then correctly produced SUPPORTS.
- [x] Tests: `uv run pytest` → **57 passed, 2 xfailed** (only Phase 5-6 remain). `ruff check`
      / `mypy src` clean.

## Done log
- 2026-08-05: Phase 0 scaffold built. `uv run pytest` → 5 passed, 10 xfailed. `ruff check`
  and `mypy src` clean.
- 2026-08-05: Phase 1 retrieval backbone implemented. Unit-test-level exit bar met; live
  exit criteria (10 real claims -> ≥5 relevant papers each) still open — deferred, see below.
- 2026-08-05: Phase 2 existence gate implemented and wired into the pipeline as the sole
  choke point (see above). Same live-validation gap as Phase 1: unit tests all mock
  `cached_get`, so this hasn't hit real Crossref yet.
- 2026-08-06: Ollama installed (`brew install ollama`, running as a `brew services` daemon)
  and `qwen3:4b` pulled. `rag.llm.get_llm().complete(...)` verified working end-to-end
  against the real local model (not mocked). Phase 0's last open item is now done.
- 2026-08-06: Phase 3 entailment implemented and live-verified against the real `qwen3:4b`
  model (see above) — the first phase with an actual live pass, not just mocked units.
  Caught and fixed two real bugs in the process (cold-load timeout, stale dispatch dict).
- 2026-08-06: S2 API key arrived; Phase 4 draft audit implemented and live-validated
  end-to-end against real S2/Crossref/Ollama (see above), which also confirmed core Phase
  1-2 mechanisms (S2 search, Crossref fuzzy-match) work against real data. Caught and fixed
  two more real bugs (404 handling, DOI-registry-mismatch abstract fetch).

## Next up
- Phase 5 (`docs/07-phase-5-limitation-extraction.md`) is the next unbuilt phase — stated +
  implicit limitation extraction, and the first phase needing full-text (not abstract-only)
  retrieval.
- Remaining live-validation gaps, now smaller: `uv sync --extra ml` (embeddings/reranking/NLI
  entailer still untested against real weights), running
  `notebooks/01_retrieval_sanity.ipynb` and `03_entailment_vs_baseline.ipynb`, seeding real
  rows into `data/eval/test_claims.jsonl` and the 3 `RETRACTED` rows in
  `existence_gold.jsonl` (a real retracted DOI still needed — today's live run didn't happen
  to hit one), and testing the GROBID/PDF path (needs `docker compose --profile phase5 up`).
- Ollama's cold-load latency (~2-3min after ~5min idle, see Phase 3) made several of today's
  live calls slow — worth keeping in mind for Phase 5/6, which will call the LLM more.

## Decisions made
- Stack locked per `01-architecture.md` (Qdrant embedded, SQLite, SPECTER2+BGE-M3, graded
  entailment, Streamlit UI, LangGraph only from Phase 4).
- Field, English-only scope, and Qwen-default LLM — recorded above.
- **Deviation from the architecture doc:** LangGraph was NOT introduced at Phase 4 despite
  `01-architecture.md` gating it to "when Phase 4 needs multi-step audit." The actual
  per-pair audit flow turned out to be a straight linear pipeline (same shape as Phase 3's
  plain-function `verify_claim`), so adding a graph framework would've been unjustified
  weight. See docs/06-phase-4-draft-audit.md for the reasoning; revisit if a later phase's
  control flow genuinely needs branching/cycles.

## Blockers / waiting on Julius
- [x] Semantic Scholar API key in `.env` — arrived and live-tested 2026-08-06.
- [x] Contact email for OpenAlex/Crossref polite pools — set 2026-08-06.
- [x] Ollama installed (v0.32.5 via Homebrew, running as a background service) +
      `qwen3:4b` pulled and smoke-tested through `llm.py` — 2026-08-06.
- [x] Docker installed (v29.2.1) — `docker-compose.yml` runs Qdrant now; GROBID is
      behind the `phase5` compose profile, not needed until then.
- All original blockers are now clear. Only remaining external dependency is a running
  GROBID instance for the PDF ingestion path, whenever that's needed.

## Parking lot (ideas, don't act yet)
- Multilingual / Chinese-language corpus — deferred; would directly address the stated
  English-only limitation if the project extends past v1.
- Browser extension / real-time — out of scope.
