"""Settings, model names, cache dir — loaded from env / .env.

Non-negotiable per docs/CONVENTIONS.md: no vendor is hardcoded elsewhere: every
module that needs a model name, API key, or endpoint reads it from `settings`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- scholarly data sources ---
    s2_api_key: str | None = None
    contact_email: str | None = None  # polite pool header for OpenAlex/Crossref

    # --- LLM provider (see llm.py — never hardcode a vendor elsewhere) ---
    llm_provider: str = "ollama"  # ollama | openai | anthropic
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # --- vector index ---
    # "embedded" = local on-disk Qdrant (no docker needed, good for Phase 1 dev).
    # "server"   = talk to the Qdrant container from docker-compose.yml.
    qdrant_mode: str = "embedded"
    qdrant_path: str = "data/qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papers"

    # --- embedding / rerank models ---
    paper_embed_model: str = "allenai/specter2"
    text_embed_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # --- entailment (Phase 3) ---
    entailment_backend: str = "llm"  # llm (Ollama, default) | nli (DeBERTa cross-encoder)
    nli_model: str = "cross-encoder/nli-deberta-v3-base"

    # --- draft audit (Phase 4) ---
    # GROBID service for PDF -> TEI (docker-compose's `grobid` service, phase5 profile —
    # named for when it was first mentioned in docs/02-data-sources.md, but PDF ingestion
    # is a Phase 4 need too). Not required for .bib/.tex ingestion.
    grobid_url: str = "http://localhost:8070"

    # --- storage ---
    cache_dir: str = "data/cache"
    sqlite_path: str = "data/rag.sqlite3"
    data_dir: str = "data"

    @property
    def cache_path(self) -> Path:
        path = REPO_ROOT / self.cache_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        path = REPO_ROOT / self.data_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
