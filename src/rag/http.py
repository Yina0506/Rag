"""Shared HTTP layer: retry+backoff, on-disk response cache, a per-host rate
limiter, and a polite User-Agent. Every external API client (S2, OpenAlex,
Crossref, ...) goes through `cached_get` — don't reach for httpx directly
elsewhere (docs/02-data-sources.md "build these in from day 1").
"""

from __future__ import annotations

import hashlib
import json
import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from rag.config import settings

_last_request_at: dict[str, float] = {}


def _cache_file(url: str, params: dict | None):
    key = hashlib.sha256(f"{url}?{json.dumps(params or {}, sort_keys=True)}".encode()).hexdigest()
    cache_dir = settings.cache_path / "http"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"


def _rate_limit(host: str, min_interval: float) -> None:
    now = time.monotonic()
    wait = _last_request_at.get(host, 0.0) + min_interval - now
    if wait > 0:
        time.sleep(wait)
    _last_request_at[host] = time.monotonic()


def _user_agent() -> str:
    contact = settings.contact_email or "no-contact-set"
    return f"rag-thesis-tool/0.1 (mailto:{contact})"


class RetryableStatus(httpx.HTTPStatusError):
    """Raised for 429/5xx so tenacity retries; anything else propagates as-is."""


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    retry=retry_if_exception_type((httpx.TransportError, RetryableStatus)),
)
def _do_get(url: str, *, params: dict | None, headers: dict) -> httpx.Response:
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params, headers=headers)
    if resp.status_code == 429 or resp.status_code >= 500:
        raise RetryableStatus(
            f"retryable status {resp.status_code}", request=resp.request, response=resp
        )
    resp.raise_for_status()
    return resp


def cached_get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    min_interval: float = 1.0,
    use_cache: bool = True,
) -> dict:
    """GET a JSON endpoint with on-disk caching + a per-host min-interval rate
    limit. Cache is unconditional (no TTL) — this project re-runs the same
    queries constantly during dev and bibliographic metadata rarely changes;
    delete `data/cache/http/` to force a refresh.
    """
    cache_file = _cache_file(url, params)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())

    _rate_limit(httpx.URL(url).host, min_interval)
    all_headers = {"User-Agent": _user_agent(), **(headers or {})}
    resp = _do_get(url, params=params, headers=all_headers)
    data = resp.json()

    if use_cache:
        cache_file.write_text(json.dumps(data))
    return data
