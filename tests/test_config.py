from rag.config import Settings


def test_settings_default_provider_is_local_ollama() -> None:
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "ollama"
    assert settings.qdrant_mode == "embedded"


def test_settings_reads_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "openai"
