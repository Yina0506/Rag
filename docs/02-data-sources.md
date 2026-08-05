# 02 — Data Sources

All primary sources are free with generous limits. This is the project's biggest strength.

## Use the OPEN scholarly-graph APIs — not publisher/aggregator websites

Important distinction: do **not** target sciencedirect.com or researchgate.net.
- **ResearchGate** — no public API; scraping violates ToS.
- **ScienceDirect (Elsevier)** — API is paywalled/restricted and covers only Elsevier's own
  journals, not the whole literature.
These are the wrong layer. Use the cross-publisher open metadata APIs below, which return
JSON over ~all of the literature.

## Metadata + abstracts

| Source | Use | Auth | Notes |
|---|---|---|---|
| **Semantic Scholar (S2)** | primary retrieval, abstracts, TLDRs, citation graph | free API key (raises rate limit) | ~200M papers, all fields; `/graph/v1/paper/search` + bulk endpoints |
| **OpenAlex** | complement / fallback, concepts, huge coverage; field-corpus building | none (polite pool: email in header) | best for building the bounded field corpus |
| **Crossref** | DOI existence validation (the gate) | none (polite pool: email in header) | authoritative for "does this paper exist" |
| **arXiv** | full-text PDFs (CS/ML/NLP) | none | heavy home for NLP/comp-creativity work; needed for passage-level (Phase 5) |

### Semantic Scholar access details (confirmed 2026)
- Request a key at https://www.semanticscholar.org/product/api (form -> key arrives by email).
- Send it on every request via the **`x-api-key`** header. Treat it as a secret.
- Without a key you share a global anonymous pool that can be throttled hard under load; a
  key gives a dedicated introductory quota (~1 req/s), raisable on request. Use **batch/bulk
  endpoints** to stay well under limits.

## Full text (Phase 5+)

- **arXiv** PDFs, **PubMed Central OA**, **CORE**, **Unpaywall** (legal OA by DOI).
- **GROBID** (self-hosted docker) to parse PDF -> structured TEI (sections, refs).

## Retraction data

- **Retraction Watch** database (now distributed via Crossref) — cross-check every paper.

## Language filter (v1 scope)

- **English-language papers only.** Filter at query time:
  - OpenAlex: use the `language` filter (`language:en`) when building the field corpus.
  - S2: filter results to English (check language field / detect from abstract) before indexing.
- Stated limitation: some primary Chinese-poetry-generation work appears in Chinese-language
  venues and will be under-represented. Note this in the thesis (see PROGRESS.md).

## Corpus strategy per pillar

- **Pillar A (verification):** no fixed corpus — retrieve live from S2/OpenAlex per claim,
  cache into local store. Vector index built over retrieved candidates + any user library.
- **Pillar B/C (limitations/directions):** build a *bounded English field corpus* first —
  pull papers matching the field intersection (evaluation of LLM/neural poetry generation,
  esp. Chinese) from OpenAlex by concept + keyword + year range + `language:en`, cap at N
  (start ~500–2000), store full metadata + citation edges. This bounded corpus is what you
  cluster over.

## Rate limits & etiquette (build these in from day 1)

- Shared HTTP client with: retry+backoff, on-disk response cache, and a global rate limiter.
- Put contact email in User-Agent for OpenAlex/Crossref polite pools; `x-api-key` for S2.
- Cache aggressively — you'll re-run the pipeline hundreds of times during dev.

## [!] THINGS YOU MUST DO YOURSELF

1. **Get a Semantic Scholar API key** — https://www.semanticscholar.org/product/api
   (free; request via form; key by email). Put it in `.env` as `S2_API_KEY`; sent as
   `x-api-key` header.
2. **Pick a contact email** for OpenAlex/Crossref polite pools -> `.env` `CONTACT_EMAIL`.
3. **Set up the LLM (local, free, no API):** install **Ollama** + `ollama pull qwen3:4b`
   (fallback `qwen3:1.7b`). Runs on M2 8GB. No API key, no cloud. Run pipeline stages
   sequentially (embed/index first, then LLM) to fit in 8GB — see PROGRESS.md LLM decision.
   `llm.py` stays provider-swappable if a stronger model is ever wanted for one eval run.
4. **Field is chosen:** evaluation of LLM/neural poetry generation, esp. Chinese (your thesis
   area) — already recorded in PROGRESS.md.
5. **Install Docker** if you want Qdrant-in-docker and GROBID (both containers). Otherwise we
   use embedded Qdrant + skip GROBID until Phase 5.
