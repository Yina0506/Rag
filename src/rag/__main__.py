"""Scaffold smoke test: `uv run python -m rag` or `docker compose run app`.

Confirms config loads and the package is importable end-to-end. Replace/extend
once `pipeline.py`'s entrypoints are implemented (Phase 1+).
"""

from __future__ import annotations

from rag.config import settings


def main() -> None:
    print(f"rag scaffold ok — provider={settings.llm_provider} qdrant_mode={settings.qdrant_mode}")


if __name__ == "__main__":
    main()
