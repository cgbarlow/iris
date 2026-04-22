"""Method-surface tests for `IrisClient` (Phase 6).

Covers each typed method as a thin wrapper over the backend HTTP surface.
Uses `respx` to mock responses — no live backend.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient
from iris_client.models.core import FileContext

BASE = "http://iris.test"


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_hits_expected_path(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/search").mock(
            return_value=httpx.Response(200, json={
                "query": "payment",
                "results": [
                    {"id": "e1", "result_type": "element", "name": "PaymentSvc"},
                ],
                "total": 1,
            }),
        )

        result = await pat_client.search("payment", limit=25)

        assert route.called
        assert route.calls.last.request.url.params["q"] == "payment"
        assert route.calls.last.request.url.params["limit"] == "25"
        assert len(result.results) == 1
        assert result.results[0].name == "PaymentSvc"


class TestDiagrams:
    @pytest.mark.asyncio
    async def test_list_diagrams_handles_items_wrapper(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json={
                "items": [{
                    "id": "d1", "diagram_type": "simple", "current_version": 1,
                    "name": "Overview", "created_at": "2026-01-01",
                    "updated_at": "2026-01-01", "data": {},
                }],
                "total": 1,
            }),
        )

        diagrams = await pat_client.list_diagrams()

        assert len(diagrams) == 1
        assert diagrams[0].name == "Overview"

    @pytest.mark.asyncio
    async def test_list_diagrams_handles_bare_list(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        # Fallback for endpoints that return a bare list (no `items` envelope).
        respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json=[
                {
                    "id": "d1", "diagram_type": "simple", "current_version": 1,
                    "name": "Overview", "created_at": "2026-01-01",
                    "updated_at": "2026-01-01", "data": {},
                },
            ]),
        )

        diagrams = await pat_client.list_diagrams()

        assert len(diagrams) == 1

    @pytest.mark.asyncio
    async def test_get_diagram(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/diagrams/d1").mock(
            return_value=httpx.Response(200, json={
                "id": "d1", "diagram_type": "simple", "current_version": 1,
                "name": "Overview", "created_at": "2026-01-01",
                "updated_at": "2026-01-01", "data": {},
            }),
        )

        diagram = await pat_client.get_diagram("d1")

        assert diagram.id == "d1"


class TestTokenManagement:
    @pytest.mark.asyncio
    async def test_create_token_round_trip(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/users/me/tokens").mock(
            return_value=httpx.Response(201, json={
                "id": "pat-1", "name": "laptop", "prefix": "abc12345",
                "created_at": "2026-01-01",
                "token": "iris_pat_abc12345_secret",
            }),
        )

        record = await pat_client.create_token("laptop")

        assert record.token.startswith("iris_pat_")
        assert record.prefix == "abc12345"


class TestExport:
    @pytest.mark.asyncio
    async def test_export_diagram_markdown_returns_bytes(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/export/diagrams/d1").mock(
            return_value=httpx.Response(
                200, content=b"# Overview\n",
                headers={"content-type": "text/markdown; charset=utf-8"},
            ),
        )

        content = await pat_client.export_diagram("d1", format="markdown")

        assert content == b"# Overview\n"

    @pytest.mark.asyncio
    async def test_export_set_json(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/export/sets/s1").mock(
            return_value=httpx.Response(200, content=b'{"schema_version":"1.0"}'),
        )

        await pat_client.export_set("s1", format="json")

        assert route.calls.last.request.url.params["format"] == "json"


class TestAsk:
    @pytest.mark.asyncio
    async def test_ask_non_streaming(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/ai/ask").mock(
            return_value=httpx.Response(200, json={
                "answer": "Payments owns credit-card tokenisation.",
                "model_used": "sonnet",
                "conversation_id": "c-1",
            }),
        )

        result = await pat_client.ask(
            "Who owns payments?",
            set_ids=["default"],
            file_contexts=[FileContext(filename="notes.md", text="PCI info")],
        )

        assert result.answer.startswith("Payments owns")
        body = route.calls.last.request.read().decode()
        assert '"set_ids":["default"]' in body
        assert '"file_contexts"' in body

    @pytest.mark.asyncio
    async def test_ask_stream_yields_events(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        sse_body = (
            b'data: {"chunk": "Hello"}\n\n'
            b'data: {"chunk": " world"}\n\n'
            b'data: {"done": true, "conversation_id": "c-1"}\n\n'
        )
        respx_mock.post(f"{BASE}/api/ai/ask").mock(
            return_value=httpx.Response(
                200, content=sse_body,
                headers={"content-type": "text/event-stream"},
            ),
        )

        events = [event async for event in await pat_client.ask_stream("Hi")]

        assert [e.kind for e in events] == ["chunk", "chunk", "done"]
        assert events[0].chunk == "Hello"
        assert events[2].conversation_id == "c-1"


class TestApplyDiagramCreation:
    @pytest.mark.asyncio
    async def test_apply_posts_diagrams_json(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(
            f"{BASE}/api/ai/sets/s1/create-diagram/apply",
        ).mock(
            return_value=httpx.Response(200, json={
                "diagram_ids": ["d-new"],
                "primary_diagram_id": "d-new",
            }),
        )

        result = await pat_client.apply_diagram_creation(
            "s1", '{"diagrams":[]}', package_id="pkg-1",
        )

        assert result.primary_diagram_id == "d-new"
        body = route.calls.last.request.read().decode()
        assert '"package_id":"pkg-1"' in body


class TestListConversations:
    @pytest.mark.asyncio
    async def test_list_conversations(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/sets/s1/conversations").mock(
            return_value=httpx.Response(200, json=[
                {
                    "id": "c-1", "set_id": "s1", "question": "Q?", "answer": "A.",
                    "created_at": "2026-01-01",
                },
            ]),
        )

        rows = await pat_client.list_conversations("s1")

        assert len(rows) == 1
        assert rows[0].question == "Q?"
