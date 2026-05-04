"""Server-Sent Events (SSE) helpers for streaming `ask` responses."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict


class AskStreamEvent(BaseModel):
    """Normalised event yielded while streaming `/api/ai/ask?stream=true`.

    The backend emits either per-chunk frames (`kind="chunk"`, with
    `chunk`), a terminating frame (`kind="done"`, with `conversation_id`
    and `model_used`), or an error frame. Unknown fields in the SSE
    payload are preserved so downstream callers can inspect them.
    """

    model_config = ConfigDict(extra="allow")

    kind: Literal["chunk", "done", "error"]
    chunk: str | None = None
    conversation_id: str | None = None
    model_used: str | None = None
    provider_name: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    duration_ms: int | None = None
    error: str | None = None


async def iter_sse_events(response: httpx.Response) -> AsyncIterator[AskStreamEvent]:
    """Yield `AskStreamEvent` objects from a live SSE response.

    The backend uses the standard SSE framing:
      data: {"chunk": "..."}\\n
      \\n
      data: {"done": true, "conversation_id": "...", ...}\\n

    We parse `data:` lines as JSON and infer `kind` from the payload
    shape:
      - `{"chunk": str}`  → kind="chunk"
      - `{"done": true, …}` → kind="done"
      - `{"error": str}`  → kind="error"
    """
    async for raw_line in response.aiter_lines():
        line = raw_line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload_str = line[len("data:"):].strip()
        if not payload_str:
            continue
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            continue
        kind = _infer_kind(payload)
        yield AskStreamEvent(kind=kind, **payload)


def _infer_kind(payload: dict[str, object]) -> Literal["chunk", "done", "error"]:
    if payload.get("done"):
        return "done"
    if "error" in payload:
        return "error"
    return "chunk"
