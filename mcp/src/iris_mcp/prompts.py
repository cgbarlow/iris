"""MCP `prompts` capability for Iris scope system prompts (ADR-152).

Surfaces every Collection / Set that has a non-empty `system_prompt`
(authored via the v5.8.0 edit screens) as a server-curated MCP prompt
named `iris:<scope_type>:<uuid>`. Claude Desktop users can invoke
these explicitly from the prompt picker; the body lands in the
conversation as a user-role message that the model treats as a
user-authored directive — not as untrusted tool data.

This is the spec-compliant replacement for the originally-planned
"silent automatic application via MCP tool data" idea, which was
correctly blocked by prompt-injection defense (see ADR-151).
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from mcp import types

if TYPE_CHECKING:
    from iris_client import IrisClient

# `iris:set:<uuid>` and `iris:collection:<uuid>` — anchored.
_NAME_RE = re.compile(r"^iris:(set|collection):([0-9a-f-]{36})$")


def _web_base() -> str | None:
    raw = os.environ.get("IRIS_WEB_URL")
    return raw.rstrip("/") if raw else None


def _scope_web_url(scope_type: str, scope_id: str) -> str | None:
    base = _web_base()
    if not base:
        return None
    return f"{base}/{scope_type}s/{scope_id}"


def _preamble(scope_type: str, scope_name: str, scope_id: str) -> str:
    """Provenance line that prefixes the system_prompt body."""
    label = scope_type.title()
    url = _scope_web_url(scope_type, scope_id)
    if url:
        return f'Loaded from Iris {label} "{scope_name}" ({url}):\n\n'
    return f'Loaded from Iris {label} "{scope_name}":\n\n'


def _short_description(scope_type: str, scope_name: str, scope_description: str | None) -> str:
    """Description shown in the MCP prompt picker.

    Format: `{Scope}: {name} — {description}` truncated at 200 chars.
    """
    label = scope_type.title()
    base = f"{label}: {scope_name}"
    if scope_description and scope_description.strip():
        combined = f"{base} — {scope_description.strip()}"
    else:
        combined = base
    if len(combined) > 200:  # noqa: PLR2004
        combined = combined[:197] + "..."
    return combined


async def list_prompts(client: IrisClient) -> list[types.Prompt]:
    """Return MCP `Prompt` objects for every scope with a system_prompt."""
    entries = await client.list_scope_prompts()
    return [
        types.Prompt(
            name=entry.name,
            description=_short_description(
                entry.scope_type, entry.scope_name, entry.description,
            ),
            arguments=[],
        )
        for entry in entries
    ]


async def get_prompt(
    client: IrisClient,
    name: str,
    _arguments: dict[str, str] | None = None,
) -> types.GetPromptResult:
    """Return the body of the named scope prompt as a single user message.

    Raises ValueError when `name` is malformed or the named scope has no
    system_prompt. The MCP server framework converts ValueErrors into the
    spec-defined error responses.
    """
    match = _NAME_RE.match(name)
    if match is None:
        msg = f"Invalid Iris scope-prompt name: {name!r}. Expected `iris:set:<uuid>` or `iris:collection:<uuid>`."
        raise ValueError(msg)

    # Resolve from the index (single backend round-trip already includes
    # the body, so we don't need a second call for `get_set` / `get_collection`).
    entries = await client.list_scope_prompts()
    entry = next((e for e in entries if e.name == name), None)
    if entry is None:
        msg = (
            f"Iris scope-prompt {name!r} not found. The scope may have been "
            "deleted, or its system_prompt was cleared."
        )
        raise ValueError(msg)

    preamble = _preamble(entry.scope_type, entry.scope_name, entry.scope_id)
    text = preamble + entry.body

    return types.GetPromptResult(
        description=_short_description(
            entry.scope_type, entry.scope_name, entry.description,
        ),
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            ),
        ],
    )
