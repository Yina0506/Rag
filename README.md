# RAG — Academic Citation Verification & Research-Direction Discovery

> **For any AI session picking this up:** read this file, then `docs/00-project-overview.md`,
> then `docs/PROGRESS.md` to see where we are. Execute the next unchecked task in the
> current phase. Update `docs/PROGRESS.md` after every work session.

## What this project is

A tool for researchers that does three connected things, each attacking a real failure
mode of using raw LLMs for research writing:

1. **Citation verification** — given a claim (or a claim+citation pair from a draft),
   retrieve *real* papers and *verify by entailment* that they actually support the claim.
   No LLM-generated citations from memory; every citation is grounded and existence-checked.
2. **Limitation & future-work extraction** — pull the stated *and implicit* limitations
   from papers in a field.
3. **Research-direction discovery** — aggregate limitations across many papers, cluster
   recurring gaps, and cross-reference the citation graph to tell *open* directions from
   already-solved ones.

The three share one backbone (retrieval + entailment over a scholarly corpus), which is
why they live in one repo.

## The core design principle (do not violate)

**The LLM never recalls bibliographic facts and never computes a verdict from memory.**
It only reasons over *retrieved* text. Retrieval + a deterministic existence gate +
entailment scoring produce every citation and every verdict. This single rule is what
makes the tool trustworthy and is the project's thesis.

## Repo layout

```
RAG/
├── README.md                 ← this file
├── docs/                     ← all planning docs (read these)
│   ├── 00-project-overview.md
│   ├── 01-architecture.md
│   ├── 02-data-sources.md
│   ├── 03-phase-1-retrieval.md
│   ├── 04-phase-2-existence-gate.md
│   ├── 05-phase-3-entailment.md
│   ├── 06-phase-4-draft-audit.md
│   ├── 07-phase-5-limitation-extraction.md
│   ├── 08-phase-6-direction-discovery.md
│   ├── 09-evaluation.md
│   ├── 10-related-work.md
│   ├── CONVENTIONS.md        ← coding conventions for AI sessions
│   └── PROGRESS.md           ← living status tracker — UPDATE EVERY SESSION
├── src/rag/                  ← the package
│   ├── config.py, models.py, llm.py, pipeline.py   ← entrypoints + shared contracts
│   ├── http.py, textutils.py                        ← shared low-level helpers
│   ├── retrieval/     ← S2/OpenAlex/Crossref clients, Qdrant index, embed/rerank, full text
│   ├── verify/         ← existence gate (Crossref), entailment (LLM + NLI backends)
│   ├── audit/           ← draft audit (.bib/.tex/PDF → per-citation report)
│   ├── limitations/      ← stated + implicit limitation extraction
│   ├── directions/        ← clustering + openness (research-direction discovery)
│   └── ui/                 ← Streamlit app (thin presentation layer over pipeline.py)
├── tests/                 ← mirrors src/rag/, 102 tests, no network/heavy deps required
├── data/                  ← gitignored except data/eval/ (versioned gold sets)
├── notebooks/
├── pyproject.toml         ← uv-managed; heavy ML deps are optional groups (ml, cluster, eval, ui)
├── Dockerfile, docker-compose.yml   ← Qdrant + app; GROBID behind a phase5 profile
└── .env.example           ← copy to .env and fill in (never commit .env)
```

## Quickstart

```
uv sync                          # core deps (fast, no ML downloads)
cp .env.example .env             # fill in S2_API_KEY, CONTACT_EMAIL
brew install ollama && ollama pull qwen3:4b   # local LLM (see docs/PROGRESS.md "LLM decision")
uv run pytest                    # 102 tests, all mocked — no network/GPU needed
```

Heavier pieces are opt-in: `uv sync --extra ml` for real embeddings/reranking/NLI-entailment,
`--extra cluster` for HDBSCAN, `--extra ui` for the Streamlit app (`make ui`),
`docker compose --profile phase5 up grobid` for PDF/full-text ingestion.

## UI

`make ui` (or `uv run streamlit run src/rag/ui/app.py`) launches a Streamlit app with four
tabs mapping to the four pipeline entrypoints: verify a claim, audit a draft's citations,
extract a paper's limitations, and discover open research directions in a field. It's a
thin rendering layer — `src/rag/ui/app.py` calls `rag.pipeline` functions and renders the
result; `styles.py`/`components.py` hold the visual system. This is a first pass, meant to
be iterated on.

## Status

All 6 build phases (`docs/03`–`08`) are implemented with passing tests (102 passed, 0
xfailed; `ruff check` / `mypy src` clean), and the `ml`/`cluster` extras have been
live-tested against real weights (three real bugs found and fixed — see `docs/PROGRESS.md`).
See `docs/PROGRESS.md` for exactly what's proven live vs. still mocked-only, and its
"Next up" for what's left (mainly: standing up a GROBID instance and assembling the actual
field corpus — neither blocks further code, both are needed before leaning on the thesis's
exit criteria). `docs/PROGRESS.md` is the authoritative living tracker; read it before this
file goes stale again.
