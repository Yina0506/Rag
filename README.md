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

## Repo layout (target)

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
├── src/rag/                  ← package (created in Phase 1)
├── tests/
├── data/                     ← gitignored; corpora, indexes, eval sets
├── notebooks/
├── pyproject.toml            ← created in Phase 0
└── .env.example              ← API keys template
```

## Status

See `docs/PROGRESS.md`. Nothing is built yet — Phase 0 (scaffold) is next.
