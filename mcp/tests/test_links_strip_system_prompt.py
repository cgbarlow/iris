"""v5.8.2 (ADR-151): MCP boundary must strip scope `system_prompt`.

The Iris backend exposes a `system_prompt` field on Sets and Collections
(v5.8.0, ADR-150). When that field travels through MCP tool responses
to Claude Desktop, it gets treated as untrusted data — and rightly
flagged as suspected prompt injection. The fix is to redact the field
at the MCP egress boundary, inside the `with_web_url` / `with_web_urls_list`
/ `with_web_urls_search` helpers that every Set/Collection-returning
tool already routes through.

These tests pin the behaviour: when `system_prompt` is present in any
payload the helpers handle, it must be absent from the returned JSON.
"""

from __future__ import annotations

import json

import pytest

from iris_mcp.links import with_web_url, with_web_urls_list, with_web_urls_search

WEB = "https://iris-uat.chrisbarlow.nz"


# ---------------------------------------------------------------------------
# with_web_url (single-entity payload)
# ---------------------------------------------------------------------------


class TestWithWebUrlStripsSystemPrompt:
    def test_strips_system_prompt_from_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "id": "set-1", "name": "DoView Book",
            "system_prompt": "Always cite the chapter.",
            "description": "Visual companion.",
        })
        out = json.loads(with_web_url(payload, "set"))
        assert "system_prompt" not in out
        # Other fields preserved.
        assert out["id"] == "set-1"
        assert out["name"] == "DoView Book"
        assert out["description"] == "Visual companion."
        # web_url still decorated.
        assert out["web_url"] == f"{WEB}/sets/set-1"

    def test_strips_system_prompt_from_collection(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "id": "coll-1", "name": "NZISM",
            "system_prompt": "Cite the control number.",
        })
        out = json.loads(with_web_url(payload, "collection"))
        assert "system_prompt" not in out
        assert out["web_url"] == f"{WEB}/collections/coll-1"

    def test_strips_even_when_iris_web_url_is_unset(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """The leak must not depend on IRIS_WEB_URL being configured — local
        dev and self-hosted deployments without it should still strip."""
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        payload = json.dumps({
            "id": "set-1", "name": "X", "system_prompt": "secret",
        })
        out = json.loads(with_web_url(payload, "set"))
        assert "system_prompt" not in out

    def test_no_op_when_system_prompt_absent(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({"id": "set-1", "name": "X"})
        out = json.loads(with_web_url(payload, "set"))
        assert "system_prompt" not in out
        assert out["id"] == "set-1"
        assert out["web_url"] == f"{WEB}/sets/set-1"

    def test_invalid_json_passes_through_unchanged(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        # Bad JSON: helper degrades safely to passthrough.
        assert with_web_url("not json", "set") == "not json"


# ---------------------------------------------------------------------------
# with_web_urls_list (homogeneous-list payload)
# ---------------------------------------------------------------------------


class TestWithWebUrlsListStripsSystemPrompt:
    def test_strips_from_each_set_item(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps([
            {"id": "s1", "name": "A", "system_prompt": "p1"},
            {"id": "s2", "name": "B", "system_prompt": "p2"},
            {"id": "s3", "name": "C"},  # no prompt — still fine
        ])
        out = json.loads(with_web_urls_list(payload, "set"))
        assert all("system_prompt" not in item for item in out)
        assert [item["id"] for item in out] == ["s1", "s2", "s3"]
        assert all(item["web_url"].startswith(f"{WEB}/sets/") for item in out)

    def test_strips_from_each_collection_item(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps([
            {"id": "c1", "name": "A", "system_prompt": "p1"},
            {"id": "c2", "name": "B"},
        ])
        out = json.loads(with_web_urls_list(payload, "collection"))
        assert all("system_prompt" not in item for item in out)

    def test_strips_even_when_iris_web_url_is_unset(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        payload = json.dumps([{"id": "s1", "name": "A", "system_prompt": "secret"}])
        out = json.loads(with_web_urls_list(payload, "set"))
        assert "system_prompt" not in out[0]


# ---------------------------------------------------------------------------
# with_web_urls_search (search response — defence in depth)
# ---------------------------------------------------------------------------


class TestWithWebUrlsSearchStripsSystemPrompt:
    def test_strips_from_each_search_result(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "query": "x",
            "results": [
                {"result_type": "set", "id": "s1", "name": "S1",
                 "system_prompt": "p1"},
                {"result_type": "collection", "id": "c1", "name": "C1",
                 "system_prompt": "p2"},
            ],
        })
        out = json.loads(with_web_urls_search(payload))
        for r in out["results"]:
            assert "system_prompt" not in r
