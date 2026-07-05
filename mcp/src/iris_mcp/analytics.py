"""GA4 Measurement Protocol event tracking for iris-mcp tool calls.

Every MCP tool dispatch emits a fire-and-forget ``mcp_tool_call`` event to
Google Analytics 4 via the Measurement Protocol, so backend tool usage
lands in the *same* GA4 property as the frontend page-view stream — no
separate stream, just the web stream's measurement ID plus a Measurement
Protocol API secret.

Tracking is a strict no-op unless BOTH of these are set, so local dev,
stdio runs, and self-hosted deployments never phone home:

* ``GA_MEASUREMENT_ID`` — the GA4 measurement ID, e.g. ``G-5B0T5HKVQ9``.
  Falls back to ``PUBLIC_GA_MEASUREMENT_ID`` (the same value the frontend
  build reads), so the shared Render env group covers both services.
* ``GA_API_SECRET`` — a Measurement Protocol API secret created under
  GA4 Admin → Data Streams → [stream] → Measurement Protocol API secrets.

Server-side events carry no real browser, so a synthetic per-process
``client_id`` / ``session_id`` is used: GA "users"/"sessions" for this
traffic approximate running server instances, while the ``mcp_tool_call``
event count and its ``tool`` parameter — the numbers that actually matter
here — stay accurate. Register ``tool`` as a custom dimension in GA4 to
slice usage by tool name.

Reference:
https://developers.google.com/analytics/devguides/collection/protocol/ga4
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx

logger = logging.getLogger(__name__)

# GA4 Measurement Protocol collection endpoint.
GA_ENDPOINT = "https://www.google-analytics.com/mp/collect"

# GA4 event name (<=40 chars, alnum + underscore, leading letter).
EVENT_NAME = "mcp_tool_call"

# Short send timeout — telemetry must never slow a tool response.
_TIMEOUT_S = 2.0

# One synthetic identity per process. All tool calls from a running
# iris-mcp instance group under it, so "users" ≈ instances and event
# counts stay true. Regenerated on restart, which is fine for telemetry.
_CLIENT_ID = uuid.uuid4().hex
_SESSION_ID = uuid.uuid4().hex

# Strong references to in-flight fire-and-forget tasks so the event loop
# does not garbage-collect them before the POST completes.
_pending: set[asyncio.Task[None]] = set()


def _measurement_id() -> str | None:
    """GA4 measurement ID, reusing the frontend's value if only that is set."""
    return os.environ.get("GA_MEASUREMENT_ID") or os.environ.get(
        "PUBLIC_GA_MEASUREMENT_ID",
    )


def _api_secret() -> str | None:
    return os.environ.get("GA_API_SECRET")


def is_enabled() -> bool:
    """True only when both the measurement ID and the API secret are set."""
    return bool(_measurement_id() and _api_secret())


def build_payload(
    tool: str,
    *,
    success: bool,
    duration_ms: float,
    client_id: str = _CLIENT_ID,
    session_id: str = _SESSION_ID,
) -> dict[str, object]:
    """Build the Measurement Protocol request body for one tool call.

    ``session_id`` and ``engagement_time_msec`` are included so the event
    registers in GA4's standard reports, not only Realtime / DebugView.
    """
    return {
        "client_id": client_id,
        "events": [
            {
                "name": EVENT_NAME,
                "params": {
                    # `tool` is the dimension worth slicing on — register it
                    # as a custom dimension in GA4 to see per-tool usage.
                    "tool": tool[:100],
                    "success": "true" if success else "false",
                    "duration_ms": int(duration_ms),
                    "session_id": session_id,
                    "engagement_time_msec": max(1, int(duration_ms)),
                },
            },
        ],
    }


async def send_event(payload: dict[str, object], *, timeout: float = _TIMEOUT_S) -> None:
    """POST an event payload to GA4. Swallows every error — telemetry is
    best-effort and must never surface to the caller."""
    measurement_id = _measurement_id()
    api_secret = _api_secret()
    if not (measurement_id and api_secret):
        return
    try:
        async with httpx.AsyncClient(timeout=timeout) as http:
            await http.post(
                GA_ENDPOINT,
                params={"measurement_id": measurement_id, "api_secret": api_secret},
                json=payload,
            )
    except Exception:
        logger.debug("iris-mcp: GA event send failed", exc_info=True)


def track_tool_call(tool: str, *, success: bool, duration_ms: float) -> None:
    """Fire-and-forget: schedule a ``mcp_tool_call`` event for ``tool``.

    Returns immediately. Does nothing when tracking is disabled or when no
    event loop is running (e.g. synchronous unit tests).
    """
    if not is_enabled():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    payload = build_payload(tool, success=success, duration_ms=duration_ms)
    task = loop.create_task(send_event(payload))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
