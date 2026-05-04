"""`iris://` MCP resources — JSON export bundles for entities (SPEC-131-A)."""

from __future__ import annotations

from iris_client import IrisClient
from mcp import types

_KINDS = ("diagrams", "elements", "packages", "sets", "collections")


def resource_list() -> list[types.Resource]:
    """Expose a scheme template per entity kind — agents fetch specific ids.

    We deliberately don't enumerate every entity here — that would be a
    large query on startup and often unhelpful. The agent is expected to
    `search` or `list_*` first, then `read_resource` for the one it wants.
    """
    return [
        types.Resource(
            uri=types.AnyUrl(f"iris://{kind}/"),
            name=f"Iris {kind.rstrip('s').capitalize()}s",
            description=(
                f"Fetch an iris://{kind}/{{id}} to get a JSON export bundle "
                "for that entity (ADR-128)."
            ),
            mimeType="application/json",
        )
        for kind in _KINDS
    ]


async def resource_read(uri: str, client: IrisClient) -> str:
    """Resolve `iris://<kind>/<id>` to the JSON export bundle."""
    if not uri.startswith("iris://"):
        raise ValueError(f"Unsupported URI scheme: {uri!r}")
    tail = uri[len("iris://"):]
    parts = tail.split("/", 1)
    if len(parts) != 2 or not parts[1]:
        raise ValueError(
            f"URI must have the form iris://<kind>/<id>; got {uri!r}",
        )
    kind, entity_id = parts
    if kind not in _KINDS:
        raise ValueError(
            f"Unsupported kind {kind!r}. Expected one of {sorted(_KINDS)}.",
        )
    method = getattr(client, f"export_{kind.rstrip('s')}")
    content: bytes = await method(entity_id, format="json")
    return content.decode("utf-8")
