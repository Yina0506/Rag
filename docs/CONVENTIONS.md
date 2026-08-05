# CONVENTIONS — for AI sessions building this repo

## Session start ritual
1. Read `README.md`, `docs/00-project-overview.md`, `docs/PROGRESS.md`.
2. Find the current phase in PROGRESS; open that phase's doc.
3. Execute the next unchecked `- [ ]` task. Don't skip ahead across phases.
4. At session end: tick completed boxes in the phase doc AND update `docs/PROGRESS.md`
   (what got done, what's next, any decisions/blockers).

## Non-negotiable design rules
- The LLM never recalls bibliographic facts or emits a verdict from memory — only reasons
  over retrieved text.
- The existence gate is a single choke point; nothing bypasses it before presentation.
- Every verdict/limitation/direction traces to a source passage or a stated assumption.
- The tool must be able to answer "no good citation / no evidence" and this is tested.

## Code
- Python 3.11+, type hints everywhere, dataclasses from `models.py` as the shared contracts.
- Keep API layer, index layer, and reasoning layer swappable (thin interfaces).
- Provider-agnostic LLM via `llm.py`; never hardcode a vendor.
- Cache all external HTTP to disk; add retry+backoff+rate-limit from day one.
- Tests for every module; mock external HTTP. No network in unit tests.
- Small, reviewable commits per task; conventional-commit style messages.

## Don't
- Don't build the UI before Phase 3.
- Don't introduce LangGraph before Phase 4 (plain functions until then).
- Don't migrate to Postgres/pgvector unless SQLite+Qdrant actually hurts.
- Don't expand scope mid-phase; note new ideas in PROGRESS "Parking lot".
