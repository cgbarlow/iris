"""Phase-2 streaming smoke tests — `iter_sse_events` parses SSE frames."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from iris_client.streaming import AskStreamEvent, iter_sse_events


class _FakeResponse:
    """Minimal stand-in for `httpx.Response` exposing `aiter_lines()`."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


@pytest.mark.asyncio
async def test_parses_chunk_then_done() -> None:
    fake = _FakeResponse([
        'data: {"chunk": "Hello"}',
        "",
        'data: {"chunk": " world"}',
        "",
        'data: {"done": true, "conversation_id": "c-1", "model_used": "sonnet"}',
        "",
    ])
    events = [ev async for ev in iter_sse_events(fake)]  # type: ignore[arg-type]

    assert [e.kind for e in events] == ["chunk", "chunk", "done"]
    assert events[0].chunk == "Hello"
    assert events[2].conversation_id == "c-1"
    assert events[2].model_used == "sonnet"


@pytest.mark.asyncio
async def test_error_frame_recognised() -> None:
    fake = _FakeResponse([
        'data: {"error": "provider unavailable"}',
        "",
    ])
    events = [ev async for ev in iter_sse_events(fake)]  # type: ignore[arg-type]

    assert len(events) == 1
    assert events[0].kind == "error"
    assert events[0].error == "provider unavailable"


@pytest.mark.asyncio
async def test_blank_and_non_data_lines_ignored() -> None:
    fake = _FakeResponse([
        "",
        ": keep-alive",
        "event: message",
        'data: {"chunk": "ok"}',
        "",
    ])
    events = [ev async for ev in iter_sse_events(fake)]  # type: ignore[arg-type]

    assert len(events) == 1
    assert events[0].chunk == "ok"


def test_event_model_defaults() -> None:
    ev = AskStreamEvent(kind="chunk", chunk="hi")
    assert ev.conversation_id is None
    assert ev.model_used is None
    assert ev.tokens_in is None
