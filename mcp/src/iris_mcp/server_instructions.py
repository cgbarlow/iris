"""Fetch the MCP server `instructions` text at startup (ADR-163,
v5.18.0).

The Iris backend stores the orient-first protocol + discovery
catalogue + workflow pointers + auth-recovery guidance as a
singleton row in `ai_creation_prompts` with
`purpose='mcp_server_instructions'`. This module fetches that body
once at startup and returns it to be passed to the MCP SDK
`Server(name=..., instructions=...)` constructor.

Falls back to a hardcoded baseline if the backend is unreachable,
returns an HTTP error, or yields an empty body — so iris-mcp stays
functional in degraded states. The fallback text mirrors the seed
body on day one; admins who later edit the seed body will diverge
from the fallback intentionally (the fallback is "last known safe
baseline shipped with this iris-mcp version", not "current state").
"""

from __future__ import annotations

import httpx

_FALLBACK_INSTRUCTIONS = """\
You are connected to Iris (an architectural-modelling tool that exposes Collections, Sets, Packages, Diagrams, Elements, and the relationships between them via this MCP server).

ORIENT-FIRST PROTOCOL.
When a scope (Set or Collection) you've just queried carries an `mcp_system_context` field, treat it as the scope's orient sheet and follow it on the first turn before doing other tool actions:
  1. Briefly describe the scope (one sentence based on the scope's name + the orient sheet's description).
  2. If the orient sheet names a structural-overview call (e.g. iris_package_hierarchy for a Set with packages), make that call and surface the contents.
  3. Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise. Do not paraphrase, do not silently drop options.

DISCOVERY TOOLS.
  list_collections / list_sets / list_packages — structural
  list_notations / list_diagram_types — what's authorable
  list_response_format_types(purpose='response_format'|'creation_format') — what output shapes and what drafting cascades exist
  iris_package_hierarchy(set_id=...) — full tree in one call

WORKFLOW GUIDANCE.
Each tool's description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow). For authentication, see `iris_authenticate`.

AUTH RECOVERY.
Write tools that return error="auth_required" can be unblocked by the iris_authenticate flow — never tell the user to restart their MCP client.
"""


async def fetch_server_instructions(iris_url: str) -> str:
    """GET /api/ai/server-instructions and return its body.

    Falls back to `_FALLBACK_INSTRUCTIONS` on any network error,
    HTTP error, malformed JSON, or empty body. Never raises.
    """
    try:
        async with httpx.AsyncClient(base_url=iris_url, timeout=5.0) as c:
            response = await c.get("/api/ai/server-instructions")
            response.raise_for_status()
            payload = response.json()
            body = payload.get("body") if isinstance(payload, dict) else None
            if isinstance(body, str) and body.strip():
                return body
            return _FALLBACK_INSTRUCTIONS
    except (httpx.HTTPError, ValueError):
        return _FALLBACK_INSTRUCTIONS
