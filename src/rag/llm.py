"""Provider-agnostic LLM wrapper.

Design rule (docs/CONVENTIONS.md): the LLM never recalls bibliographic facts or
emits a verdict from memory — every caller passes it the retrieved evidence text
and the LLM only reasons over that. This module is just plumbing; callers own
the "ground everything in retrieved text" discipline.

Default provider is local Ollama (see docs/PROGRESS.md "LLM decision": qwen3:4b
on an 8GB M2, no API key, no cloud). OpenAI/Anthropic are drop-in alternatives
behind the same interface for a one-off stronger-model comparison run.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

import httpx

from rag.config import settings


class LLMClient(Protocol):
    def complete(self, prompt: str, *, system: str | None = None) -> str: ...


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str: ...


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
        }
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
        return resp.json()["response"]


class OpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.model = model

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError("Wire up when a comparison run is actually needed")


class AnthropicClient(BaseLLMClient):
    def __init__(self, model: str = "claude-sonnet-5") -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.model = model

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError("Wire up when a comparison run is actually needed")


def get_llm(provider: str | None = None) -> BaseLLMClient:
    """Return the configured LLM client. Never hardcode a vendor at call sites."""
    provider = provider or settings.llm_provider
    if provider == "ollama":
        return OllamaClient()
    if provider == "openai":
        return OpenAIClient()
    if provider == "anthropic":
        return AnthropicClient()
    raise ValueError(f"Unknown LLM provider: {provider}")
