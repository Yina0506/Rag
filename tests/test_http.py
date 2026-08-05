from __future__ import annotations

import httpx
import pytest

from rag import http as rag_http


def _fake_response(json_data: dict) -> httpx.Response:
    return httpx.Response(200, json=json_data, request=httpx.Request("GET", "https://example.com"))


@pytest.fixture
def cache_dir(tmp_path, mocker):
    mocker.patch.object(
        type(rag_http.settings),
        "cache_path",
        new_callable=mocker.PropertyMock,
        return_value=tmp_path,
    )
    return tmp_path


def test_cached_get_hits_network_once_then_reads_from_disk(cache_dir, mocker) -> None:
    do_get = mocker.patch.object(rag_http, "_do_get", return_value=_fake_response({"ok": True}))
    mocker.patch.object(rag_http, "_rate_limit")

    first = rag_http.cached_get("https://example.com/search", params={"q": "x"})
    second = rag_http.cached_get("https://example.com/search", params={"q": "x"})

    assert first == {"ok": True}
    assert second == {"ok": True}
    do_get.assert_called_once()


def test_cached_get_bypasses_cache_when_disabled(cache_dir, mocker) -> None:
    do_get = mocker.patch.object(rag_http, "_do_get", return_value=_fake_response({"ok": True}))
    mocker.patch.object(rag_http, "_rate_limit")

    rag_http.cached_get("https://example.com/search", use_cache=False)
    rag_http.cached_get("https://example.com/search", use_cache=False)

    assert do_get.call_count == 2


def test_user_agent_includes_contact_email(mocker) -> None:
    mocker.patch.object(rag_http.settings, "contact_email", "me@example.com")
    assert "me@example.com" in rag_http._user_agent()
