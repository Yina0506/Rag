# 01 — Architecture

## System diagram

```
                         ┌───────────────────────────┐
                         │  Interface (Streamlit v1)  │
                         │  - claim box / draft upload │
                         │  - field explorer (Pillar C)│
                         └─────────────┬───────────────┘
                                       │
                    ┌──────────────────┴───────────────────┐
                    │        Orchestration (src/rag)         │
                    │  routes: verify_claim, audit_draft,    │
                    │          extract_limitations,          │
                    │          discover_directions           │
                    └───┬──────────┬───────────┬─────────────┘
                        │          │           │
              ┌─────────▼──┐ ┌─────▼──────┐ ┌──▼───────────────┐
              │ Retrieval  │ │ Existence  │ │ Entailment       │
              │ - S2/OA API│ │ gate       │ │ - NLI model      │
              │ - vector   │ │ - Crossref │ │   (abstract/     │
              │   index    │ │   DOI      │ │    passage vs     │
              │   (Qdrant) │ │ - retract  │ │    claim)         │
              │ - reranker │ │   check    │ │ - LLM justify     │
              └─────┬──────┘ └─────┬──────┘ └──┬───────────────┘
                    │              │           │
              ┌─────▼──────────────▼───────────▼──────────────┐
              │ Corpus + metadata store                        │
              │ - papers (id, doi, title, abstract, year, ...) │
              │ - full text (Phase 5+)                          │
              │ - citation edges (for "still open?" in C)       │
              │ Postgres + pgvector  OR  Qdrant + SQLite        │
              └────────────────────────────────────────────────┘
```

## Tech stack (decisions locked for v1)

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | ecosystem |
| Package mgmt | `uv` + `pyproject.toml` | fast, modern; fall back to pip if unavailable |
| Orchestration | plain Python modules first; **LangGraph** only when Phase 4 needs multi-step audit | avoid premature framework weight |
| Retrieval index | **Qdrant** (local docker or embedded) | filtering by year/venue, open source |
| Metadata store | **SQLite** for v1 (papers + citation edges) | zero-setup; migrate to Postgres+pgvector only if needed |
| Embeddings | **SPECTER2** (paper-level) + **BGE-M3** (passage/claim-level) | SPECTER2 is built for scientific similarity; BGE-M3 multilingual & long-context |
| Reranker | **BGE-reranker-v2-m3** cross-encoder | biggest lever on mismatch reduction |
| Entailment | DeBERTa-NLI fine-tune **or** LLM-as-entailer with structured output | start with LLM-as-entailer (faster to stand up), compare to NLI model in eval |
| LLM | configurable via a thin wrapper (OpenAI/Anthropic/local Qwen) | don't hardcode a provider |
| Paper parsing | **GROBID** (Phase 4/5, for PDFs & bib) | standard for scholarly PDF/TEI |
| Clustering (Pillar C) | embeddings + HDBSCAN | density clustering, no preset k |
| UI | **Streamlit** | pipeline is the thesis, not the UI |
| Eval | **RAGAS** + custom gold sets | see `09-evaluation.md` |

## Key module boundaries (create in Phase 1)

```
src/rag/
├── config.py          # settings, model names, API keys from env
├── models.py          # dataclasses: Paper, Claim, Candidate, Verdict, Limitation, Direction
├── llm.py             # provider-agnostic LLM wrapper
├── retrieval/
│   ├── sources.py     # Semantic Scholar / OpenAlex / arXiv clients
│   ├── index.py       # Qdrant wrapper: build, upsert, search
│   ├── embed.py       # SPECTER2 + BGE-M3 embedding fns
│   └── rerank.py      # cross-encoder rerank
├── verify/
│   ├── existence.py   # Crossref DOI resolution + retraction check
│   └── entailment.py  # claim vs evidence → graded verdict
├── audit/
│   └── draft.py       # GROBID parse + per-(claim,cite) audit (Phase 4)
├── limitations/
│   └── extract.py     # stated + implicit limitation extraction (Phase 5)
├── directions/
│   ├── cluster.py     # aggregate + HDBSCAN cluster limitations (Phase 6)
│   └── openness.py    # citation-graph "still open?" check (Phase 6)
└── pipeline.py        # the 4 entrypoints that the UI calls
```

## Data contracts (define concretely in Phase 1, models.py)

- `Paper{ id, doi, title, abstract, year, venue, authors[], citations[], retracted:bool }`
- `Claim{ text, source_span?, extracted_from? }`
- `Candidate{ paper, score, retrieved_passage? }`
- `Verdict{ claim, paper, grade∈{SUPPORTS,WEAK,NEUTRAL,CONTRADICTS,NOT_FOUND}, evidence_passage, confidence, justification }`
- `Limitation{ paper_id, text, type∈{stated,implicit}, topic_embedding }`
- `Direction{ label, member_limitations[], frequency, still_open:bool, solving_papers[] }`

Keeping these stable lets each phase be built independently.
