"""v5.6.1: tests for the web-URL link decorator (links.py).

The decorator is what stops MCP-using LLMs from guessing the iris web
URL when they cite an entity. Without IRIS_WEB_URL configured the
decoration is a no-op and tool output is unchanged from prior versions.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools
from iris_mcp.links import (
    decorate_item,
    decorate_search,
    web_base,
    web_url_for,
    with_web_url,
    with_web_urls_list,
    with_web_urls_search,
)

BASE = "http://iris.test"
WEB = "https://iris-uat.chrisbarlow.nz"


class TestWebUrlFor:
    def test_returns_none_when_base_unset(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        assert web_url_for("diagram", "abc") is None

    def test_returns_none_for_unknown_kind(self) -> None:
        assert web_url_for("nope", "abc", base=WEB) is None

    def test_returns_none_for_empty_id(self) -> None:
        assert web_url_for("diagram", "", base=WEB) is None

    @pytest.mark.parametrize(
        ("kind", "path"),
        [
            ("diagram", "views"),
            ("diagrams", "views"),
            ("element", "elements"),
            ("package", "packages"),
            ("set", "sets"),
            ("collection", "collections"),
        ],
    )
    def test_routes_each_kind_to_frontend_path(self, kind: str, path: str) -> None:
        assert web_url_for(kind, "x-1", base=WEB) == f"{WEB}/{path}/x-1"

    def test_strips_trailing_slash_via_web_base(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", "https://iris.example.com/")
        assert web_base() == "https://iris.example.com"
        assert web_url_for("diagram", "x") == "https://iris.example.com/views/x"


class TestDecorateItem:
    def test_attaches_web_url_to_dict(self) -> None:
        item = {"id": "abc", "name": "thing"}
        decorate_item(item, "diagram", WEB)
        assert item["web_url"] == f"{WEB}/views/abc"

    def test_does_not_overwrite_existing_web_url(self) -> None:
        item = {"id": "abc", "web_url": "https://kept"}
        decorate_item(item, "diagram", WEB)
        assert item["web_url"] == "https://kept"

    def test_skips_when_id_missing(self) -> None:
        item = {"name": "no id"}
        decorate_item(item, "diagram", WEB)
        assert "web_url" not in item


class TestDecorateSearch:
    def test_decorates_each_result_by_result_type(self) -> None:
        payload = {
            "query": "x",
            "results": [
                {"id": "d1", "result_type": "diagram", "name": "Diag"},
                {"id": "e1", "result_type": "element", "name": "Elem"},
                {"id": "s1", "result_type": "set", "name": "Set"},
            ],
            "total": 3,
        }
        decorate_search(payload, WEB)
        urls = [r["web_url"] for r in payload["results"]]
        assert urls == [
            f"{WEB}/views/d1",
            f"{WEB}/elements/e1",
            f"{WEB}/sets/s1",
        ]


class TestWrappers:
    def test_with_web_url_noop_when_unset(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        original = '{"id": "abc"}'
        assert with_web_url(original, "diagram") == original

    def test_with_web_url_decorates_when_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        decorated = with_web_url('{"id": "abc"}', "diagram")
        body = json.loads(decorated)
        assert body["web_url"] == f"{WEB}/views/abc"

    def test_with_web_urls_list_decorates_each(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        decorated = with_web_urls_list(
            '[{"id": "a"}, {"id": "b"}]', "set",
        )
        body = json.loads(decorated)
        assert body[0]["web_url"] == f"{WEB}/sets/a"
        assert body[1]["web_url"] == f"{WEB}/sets/b"

    def test_with_web_urls_search_decorates_results(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        decorated = with_web_urls_search(
            json.dumps({
                "query": "q",
                "results": [{"id": "d1", "result_type": "diagram"}],
                "total": 1,
            }),
        )
        body = json.loads(decorated)
        assert body["results"][0]["web_url"] == f"{WEB}/views/d1"

    def test_invalid_json_passes_through(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        assert with_web_url("not json", "diagram") == "not json"


# ----- end-to-end through the dispatch layer ---------------------------------


class TestToolsDispatchWithWebUrl:
    @pytest.mark.asyncio
    async def test_get_diagram_includes_web_url(
        self,
        client: IrisClient,
        respx_mock: respx.Router,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        respx_mock.get(f"{BASE}/api/diagrams/d-42").mock(
            return_value=httpx.Response(200, json={
                "id": "d-42", "name": "Demo",
                "diagram_type": "process", "current_version": 1,
                "created_at": "2026-05-07T00:00:00Z",
                "updated_at": "2026-05-07T00:00:00Z",
            }),
        )
        result = await tools.dispatch("get_diagram", client, {"diagram_id": "d-42"})
        body = json.loads(result[0].text)
        assert body["web_url"] == f"{WEB}/views/d-42"

    @pytest.mark.asyncio
    async def test_search_includes_per_result_web_urls(
        self,
        client: IrisClient,
        respx_mock: respx.Router,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        respx_mock.get(f"{BASE}/api/search").mock(
            return_value=httpx.Response(200, json={
                "query": "demo",
                "results": [
                    {"id": "d-1", "result_type": "diagram", "name": "D"},
                    {"id": "e-1", "result_type": "element", "name": "E"},
                ],
                "total": 2,
            }),
        )
        result = await tools.dispatch("search", client, {"query": "demo"})
        body = json.loads(result[0].text)
        urls = [r["web_url"] for r in body["results"]]
        assert urls == [f"{WEB}/views/d-1", f"{WEB}/elements/e-1"]

    @pytest.mark.asyncio
    async def test_no_web_url_when_env_unset(
        self,
        client: IrisClient,
        respx_mock: respx.Router,
        monkeypatch,  # type: ignore[no-untyped-def]
    ) -> None:
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        respx_mock.get(f"{BASE}/api/diagrams/d-42").mock(
            return_value=httpx.Response(200, json={
                "id": "d-42", "name": "Demo",
                "diagram_type": "process", "current_version": 1,
                "created_at": "2026-05-07T00:00:00Z",
                "updated_at": "2026-05-07T00:00:00Z",
            }),
        )
        result = await tools.dispatch("get_diagram", client, {"diagram_id": "d-42"})
        body = json.loads(result[0].text)
        assert "web_url" not in body
