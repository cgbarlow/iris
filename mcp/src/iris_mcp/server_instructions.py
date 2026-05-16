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
  2. INVOKE the structural-overview call the orient sheet names (typically `package_hierarchy` for a Set with packages). Surface the resulting tree to the user as part of the orient — NOT as a follow-up "want me to load it?" prompt. If your MCP client lazy-loads tools and the named tool isn't currently in your toolset, request/load it before continuing. The TOC is part of the orient, not optional.
  3. Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise. Do not paraphrase, do not silently drop options.

ASKING QUESTIONS.
Whenever you need the user to choose from a finite set of options, ask via the MCP client's structured user-question tool (AskUserQuestion in Claude Code / Claude Desktop / Cursor). Do not embed multi-option questions in prose. Do not list multiple questions in a single message — one question per turn, wait for the answer, then ask the next. When the client does not expose a user-question tool, fall back to a numbered list with options IN ORDER, VERBATIM (no paraphrasing).
This applies to:
  - the orient menu (already covered in ORIENT-FIRST above),
  - every Stage-0 setup question in a creation cascade,
  - the save-destination chooser,
  - any other choice the model surfaces to the user.
If you ever feel unsure whether a question warrants the tool: it does.

DISCOVERY TOOLS.
  list_collections / list_sets / list_packages — structural
  list_notations / list_diagram_types — what's authorable
  list_response_format_types(purpose='response_format'|'creation_format') — what output shapes and what drafting cascades exist
  package_hierarchy(set_id=...) — full tree in one call

WORKFLOW GUIDANCE.
Each tool's description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow).

AUTH RECOVERY.
If a write tool returns error="auth_required", the user needs to sign in to Iris in their MCP client. Tell them: in claude.ai go to Settings → Connectors → Iris and click "Connect" / "Sign in"; a browser tab opens for sign-in and consent. They will NOT be asked for a client_id or secret — Dynamic Client Registration (RFC 7591) handles that automatically. If no sign-in button appears, try removing and re-adding the connector. Read tools (search, get_*, list_*, package_hierarchy) work without sign-in; only writes (create_*, update_*) need it. Don't call any auth-related tool yourself — the OAuth handshake is between the MCP client and Iris.
"""


async def fetch_server_instructions(iris_url: str) -> str:
    """GET /api/ai/server-instructions and return its body.

    Falls back to `_FALLBACK_INSTRUCTIONS` on any network error,
    HTTP error, malformed JSON, or empty body. Never raises.

    Used by the lifespan startup fetch — the caller wants a usable
    body in hand before serving the first request, so falling back to
    the hardcoded baseline is the right behaviour. The refresh-loop
    variant `try_fetch_server_instructions` returns `None` instead, so
    a transient backend failure mid-loop doesn't clobber a previously-
    fetched admin-edited body with the baseline (ADR-166, v6.0.5).
    """
    body = await try_fetch_server_instructions(iris_url)
    return body if body is not None else _FALLBACK_INSTRUCTIONS


async def try_fetch_server_instructions(iris_url: str) -> str | None:
    """GET /api/ai/server-instructions and return its body, or None.

    Returns `None` on any failure mode that `fetch_server_instructions`
    falls back from — network error, HTTP error, malformed JSON, empty
    body, whitespace-only body. Never raises.

    Used by the v6.0.5 refresh loop (ADR-166): if the backend is
    transiently unavailable mid-loop, the caller preserves the last
    good body rather than overwriting it with the hardcoded fallback.
    The lifespan startup path uses `fetch_server_instructions` so the
    very first request still sees a non-`None` body.
    """
    try:
        async with httpx.AsyncClient(base_url=iris_url, timeout=5.0) as c:
            response = await c.get("/api/ai/server-instructions")
            response.raise_for_status()
            payload = response.json()
            body = payload.get("body") if isinstance(payload, dict) else None
            if isinstance(body, str) and body.strip():
                return body
            return None
    except (httpx.HTTPError, ValueError):
        return None
