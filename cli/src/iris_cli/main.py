"""Typer entry point for the `iris` CLI (ADR-130 / SPEC-130-A).

Commands are grouped by entity / concern. All async calls to the backend
route through a single `iris_client.IrisClient` instance configured via
`iris_cli.config.load`.

v6.4.0 (ADR-180): adds write-tool parity with MCP. New sub-apps:
`iris create`, `iris update`, `iris move`, `iris render`. Existing
`iris export` is read-only; `iris render` is the artefact pipeline
(md/docx/pdf via the v6.2.0 renderer).
"""

from __future__ import annotations

import asyncio
import getpass
import json as json_lib
import socket
import sys
from pathlib import Path
from typing import Any

import httpx
import typer
from iris_client import IrisAuthError, IrisClient, IrisClientError, IrisHTTPError

from iris_cli import config as cfg
from iris_cli import output

app = typer.Typer(
    name="iris",
    help="Command-line interface for Iris.",
    no_args_is_help=True,
)

# --- Sub-apps per entity group ----------------------------------------------

diagrams_app = typer.Typer(help="Diagram commands.", no_args_is_help=True)
elements_app = typer.Typer(help="Element commands.", no_args_is_help=True)
packages_app = typer.Typer(help="Package commands.", no_args_is_help=True)
sets_app = typer.Typer(help="Set commands.", no_args_is_help=True)
collections_app = typer.Typer(help="Collection commands.", no_args_is_help=True)
export_app = typer.Typer(help="Export entities as JSON or Markdown (read-only).", no_args_is_help=True)
conversations_app = typer.Typer(help="Conversation commands.", no_args_is_help=True)

# v6.4.0 (ADR-180): write-tool parity with MCP.
create_app = typer.Typer(help="Create new entities.", no_args_is_help=True)
update_app = typer.Typer(help="Update entity metadata (partial).", no_args_is_help=True)
move_app = typer.Typer(help="Re-parent entities (diagram / package / set).", no_args_is_help=True)
render_app = typer.Typer(help="Render diagrams or markdown to md/docx/pdf artefacts.", no_args_is_help=True)

app.add_typer(diagrams_app, name="diagrams")
app.add_typer(elements_app, name="elements")
app.add_typer(packages_app, name="packages")
app.add_typer(sets_app, name="sets")
app.add_typer(collections_app, name="collections")
app.add_typer(export_app, name="export")
app.add_typer(conversations_app, name="conversations")
app.add_typer(create_app, name="create")
app.add_typer(update_app, name="update")
app.add_typer(move_app, name="move")
app.add_typer(render_app, name="render")


# --- Global context ---------------------------------------------------------


class _State:
    url: str | None = None
    token: str | None = None
    as_json: bool = False


state = _State()


@app.callback()
def _global_options(
    ctx: typer.Context,
    url: str | None = typer.Option(None, "--url", envvar="IRIS_URL", help="Iris base URL."),
    token: str | None = typer.Option(
        None, "--token", envvar="IRIS_TOKEN", help="Personal Access Token or JWT.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    resolved = cfg.load(url_flag=url, token_flag=token)
    state.url = resolved.url
    state.token = resolved.token
    state.as_json = json_output
    ctx.obj = state


def _client() -> IrisClient:
    return IrisClient(url=state.url, token=state.token)


def _run(coro: Any) -> Any:
    try:
        return asyncio.run(coro)
    except IrisAuthError as exc:
        output.print_error(f"{exc.detail} (run `iris login`?)")
        raise typer.Exit(code=3) from exc
    except IrisClientError as exc:
        output.print_error(str(exc))
        raise typer.Exit(code=1) from exc
    except httpx.HTTPError as exc:
        output.print_error(f"network: {exc}")
        raise typer.Exit(code=2) from exc


# --- Auth -------------------------------------------------------------------


@app.command()
def login(
    url: str | None = typer.Option(None, "--url", help="Override base URL for this login."),
    username: str | None = typer.Option(
        None, "--username", envvar="IRIS_USERNAME", help="Username (prompt if omitted).",
    ),
    password: str | None = typer.Option(
        None, "--password", envvar="IRIS_PASSWORD", help="Password (prompt if omitted).",
    ),
    token_name: str | None = typer.Option(
        None, "--token-name", help="Label for the stored PAT.",
    ),
    token: str | None = typer.Option(
        None, "--token",
        help=(
            "Use an existing PAT instead of minting a new one. Required for "
            "Supabase-deployment backends, where /api/auth/login is disabled "
            "and PATs must be minted via Supabase Auth + POST "
            "/api/users/me/tokens."
        ),
    ),
) -> None:
    """Log in and save credentials to ~/.config/iris/config.toml.

    Two paths:

    1. SQLite-mode backend (default): username + password ->
       /api/auth/login -> mint a new PAT -> store it. Pass --username
       / --password or be prompted.

    2. Supabase-mode backend (UAT, prod): /api/auth/login is disabled;
       auth is handled by Supabase. Mint a PAT externally (via the
       frontend or curl with a Supabase JWT) and pass it here as
       --token. The CLI just saves { url, token } to disk -- no API
       call.
    """
    final_url = url or state.url or cfg.DEFAULT_URL

    if token:
        # Path 2: caller already has a PAT. Just persist it; no API call.
        saved_to = cfg.save(final_url, token)
        typer.echo(f"Saved PAT to {saved_to}")
        return

    # Path 1: SQLite-mode interactive flow.
    user = username or typer.prompt("Username")
    pw = password or getpass.getpass("Password: ")
    name = token_name or f"iris-cli@{socket.gethostname()}"

    async def _do() -> Path:
        async with IrisClient(url=final_url, token=None) as c:
            login_resp = await c.login(user, pw)
            # Swap to the JWT-authenticated client to mint a PAT.
            async with IrisClient(url=final_url, token=login_resp.access_token) as auth_c:
                pat = await auth_c.create_token(name)
        return cfg.save(final_url, pat.token)

    try:
        saved_to = _run(_do())
    except IrisHTTPError as exc:
        if exc.status_code == 404 and "Supabase" in (exc.detail or ""):
            output.print_error(
                "This backend runs in Supabase deployment mode — "
                "/api/auth/login is disabled. Mint a PAT externally "
                "(via the frontend or curl + a Supabase JWT) and re-run:\n\n"
                f"  iris login --url {final_url} --token iris_pat_…",
            )
            raise typer.Exit(code=1) from exc
        raise

    typer.echo(f"Logged in. PAT stored at {saved_to}")


@app.command()
def whoami() -> None:
    """Show the authenticated user."""

    async def _do() -> dict[str, Any]:
        async with _client() as c:
            if c.is_anonymous:
                return {"anonymous": True, "url": state.url}
            me = await c.whoami()
            return me.model_dump()

    me = _run(_do())
    if state.as_json:
        output.print_json(me)
    else:
        for k, v in me.items():
            typer.echo(f"{k}: {v}")


# --- Search -----------------------------------------------------------------


@app.command()
def search(
    q: str = typer.Argument(..., help="Query string."),
    set_id: str | None = typer.Option(None, "--set", help="Scope to a set."),
    collection_id: str | None = typer.Option(
        None, "--collection", help="Scope to a collection.",
    ),
    limit: int = typer.Option(50, "--limit", min=1, max=200),
) -> None:
    """Full-text search across entities."""

    async def _do() -> Any:
        async with _client() as c:
            return await c.search(
                q, set_id=set_id, collection_id=collection_id, limit=limit,
            )

    result = _run(_do())
    if state.as_json:
        output.print_json(result)
    else:
        output.print_table(
            result.results,
            columns=["result_type", "name", "type_detail", "set_name"],
            title=f"Search: {q} ({result.total})",
        )


# --- Diagrams ---------------------------------------------------------------


@diagrams_app.command("list")
def diagrams_list(
    set_id: str | None = typer.Option(None, "--set"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(50, "--page-size", min=1, max=200),
) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.list_diagrams(
                set_id=set_id, page=page, page_size=page_size,
            )

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(
            rows,
            columns=["id", "name", "diagram_type", "notation", "updated_at"],
            title=f"Diagrams ({len(rows)})",
        )


@diagrams_app.command("get")
def diagrams_get(diagram_id: str) -> None:
    async def _do() -> Any:
        async with _client() as c:
            return await c.get_diagram(diagram_id)

    diagram = _run(_do())
    if state.as_json:
        output.print_json(diagram)
    else:
        d = diagram.model_dump()
        for k in ("id", "name", "diagram_type", "notation", "current_version", "updated_at"):
            typer.echo(f"{k}: {d.get(k)}")


@diagrams_app.command("versions")
def diagrams_versions(diagram_id: str) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.get_diagram_versions(diagram_id)

    versions = _run(_do())
    if state.as_json:
        output.print_json(versions)
    else:
        output.print_table(
            versions,
            columns=["version", "name", "change_type", "created_at"],
            title=f"Versions of {diagram_id}",
        )


# --- Elements ---------------------------------------------------------------


@elements_app.command("list")
def elements_list(
    set_id: str | None = typer.Option(None, "--set"),
    package_id: str | None = typer.Option(
        None, "--package-id",
        help="Filter by package. Pass 'null' to list elements with no package.",
    ),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(50, "--page-size", min=1, max=200),
) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            params: dict[str, Any] = {"page": page, "page_size": page_size}
            if set_id is not None:
                params["set_id"] = set_id
            if package_id is not None:
                params["package_id"] = package_id
            resp = await c._request("GET", "/api/elements", params=params)
            return resp.json().get("items", [])

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(
            rows,
            columns=["id", "name", "element_type", "notation", "updated_at"],
            title=f"Elements ({len(rows)})",
        )


@elements_app.command("get")
def elements_get(element_id: str) -> None:
    async def _do() -> Any:
        async with _client() as c:
            return await c.get_element(element_id)

    element = _run(_do())
    if state.as_json:
        output.print_json(element)
    else:
        d = element.model_dump()
        for k in ("id", "name", "element_type", "notation", "current_version"):
            typer.echo(f"{k}: {d.get(k)}")


# --- Packages / Sets / Collections ------------------------------------------


@packages_app.command("list")
def packages_list(set_id: str | None = typer.Option(None, "--set")) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.list_packages(set_id=set_id)

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(rows, columns=["id", "name", "parent_package_id"], title="Packages")


@packages_app.command("list-elements")
def packages_list_elements_cmd(
    package_id: str = typer.Argument(...),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(50, "--page-size", min=1, max=200),
) -> None:
    """List elements that belong to a package (ADR-184)."""
    async def _do() -> list[Any]:
        async with _client() as c:
            resp = await c._request(
                "GET",
                f"/api/packages/{package_id}/elements",
                params={"page": page, "page_size": page_size},
            )
            return resp.json().get("items", [])

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(
            rows,
            columns=["id", "name", "element_type", "notation", "updated_at"],
            title=f"Elements in package {package_id} ({len(rows)})",
        )


@packages_app.command("get")
def packages_get(package_id: str) -> None:
    async def _do() -> Any:
        async with _client() as c:
            return await c.get_package(package_id)

    if state.as_json:
        output.print_json(_run(_do()))
    else:
        output.print_json(_run(_do()))  # scalar get -> always json-ish


@sets_app.command("list")
def sets_list(collection_id: str | None = typer.Option(None, "--collection")) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.list_sets(collection_id=collection_id)

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(rows, columns=["id", "name", "collection_id"], title="Sets")


@sets_app.command("get")
def sets_get(set_id: str) -> None:
    async def _do() -> Any:
        async with _client() as c:
            return await c.get_set(set_id)

    output.print_json(_run(_do()))


@collections_app.command("list")
def collections_list() -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.list_collections()

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(rows, columns=["id", "name"], title="Collections")


@collections_app.command("get")
def collections_get(collection_id: str) -> None:
    async def _do() -> Any:
        async with _client() as c:
            return await c.get_collection(collection_id)

    output.print_json(_run(_do()))


# --- Export -----------------------------------------------------------------


def _export(
    kind: str,
    entity_id: str,
    fmt: str,
    out_path: Path | None,
) -> None:
    async def _do() -> bytes:
        async with _client() as c:
            method = getattr(c, f"export_{kind}")
            return await method(entity_id, format=fmt)

    content = _run(_do())
    if out_path is None or str(out_path) == "-":
        sys.stdout.buffer.write(content)
        sys.stdout.flush()
    else:
        out_path.write_bytes(content)
        typer.echo(f"Wrote {len(content)} bytes to {out_path}")


_FORMAT_OPTION = typer.Option(..., "--format", help="json or markdown")
_OUT_OPTION = typer.Option(
    None, "-o", "--output", help="Output path (or `-` for stdout).",
)


@export_app.command("diagram")
def export_diagram_cmd(
    diagram_id: str, format: str = _FORMAT_OPTION, out: Path | None = _OUT_OPTION,
) -> None:
    _export("diagram", diagram_id, format, out)


@export_app.command("element")
def export_element_cmd(
    element_id: str, format: str = _FORMAT_OPTION, out: Path | None = _OUT_OPTION,
) -> None:
    _export("element", element_id, format, out)


@export_app.command("package")
def export_package_cmd(
    package_id: str, format: str = _FORMAT_OPTION, out: Path | None = _OUT_OPTION,
) -> None:
    _export("package", package_id, format, out)


@export_app.command("set")
def export_set_cmd(
    set_id: str, format: str = _FORMAT_OPTION, out: Path | None = _OUT_OPTION,
) -> None:
    _export("set", set_id, format, out)


@export_app.command("collection")
def export_collection_cmd(
    collection_id: str, format: str = _FORMAT_OPTION, out: Path | None = _OUT_OPTION,
) -> None:
    _export("collection", collection_id, format, out)


# --- Ask --------------------------------------------------------------------


@app.command()
def ask(
    question: str,
    set_ids: list[str] = typer.Option(  # noqa: B008 — Typer idiom
        [], "--set", help="Set IDs (repeatable).",
    ),
    collection_id: str | None = typer.Option(None, "--collection"),
    mode: str = typer.Option("discuss", "--mode", help="discuss or creation"),
    notation: str | None = typer.Option(None, "--notation"),
    thread_id: str | None = typer.Option(None, "--thread"),
    stream: bool = typer.Option(
        True, "--stream/--no-stream", help="Stream tokens to stdout.",
    ),
    provider_id: str | None = typer.Option(None, "--provider"),
) -> None:
    """Ask the AI a question about one or more sets."""

    async def _stream() -> None:
        async with _client() as c:
            async for event in await c.ask_stream(
                question,
                set_ids=set_ids or None,
                collection_id=collection_id,
                mode=mode,
                notation=notation,
                thread_id=thread_id,
                provider_id=provider_id,
            ):
                if event.kind == "chunk" and event.chunk:
                    sys.stdout.write(event.chunk)
                    sys.stdout.flush()
                elif event.kind == "done":
                    sys.stdout.write("\n")
                    if event.conversation_id:
                        sys.stderr.write(f"\nConversation: {event.conversation_id}\n")
                elif event.kind == "error" and event.error:
                    output.print_error(event.error)

    async def _single() -> Any:
        async with _client() as c:
            return await c.ask(
                question,
                set_ids=set_ids or None,
                collection_id=collection_id,
                mode=mode,
                notation=notation,
                thread_id=thread_id,
                provider_id=provider_id,
            )

    if state.as_json or not stream:
        result = _run(_single())
        if state.as_json:
            output.print_json(result)
        else:
            typer.echo(result.answer)
    else:
        _run(_stream())


@conversations_app.command("list")
def conversations_list(
    set_id: str = typer.Option(..., "--set", help="Set ID."),
    limit: int = typer.Option(50, "--limit", min=1, max=200),
) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.list_conversations(set_id, limit=limit)

    rows = _run(_do())
    if state.as_json:
        output.print_json(rows)
    else:
        output.print_table(
            rows,
            columns=["id", "question", "model_used", "created_at"],
            title=f"Conversations in {set_id}",
        )


# --- v6.4.0 (ADR-180) write-tool parity with MCP ---------------------------


def _parse_json_opt(raw: str | None, flag: str) -> dict[str, Any] | None:
    """Parse a JSON dict from a CLI flag; bail with a clear error on bad JSON."""
    if raw is None:
        return None
    try:
        parsed = json_lib.loads(raw)
    except json_lib.JSONDecodeError as exc:
        output.print_error(f"{flag}: invalid JSON ({exc})")
        raise typer.Exit(code=1) from exc
    if not isinstance(parsed, dict):
        output.print_error(f"{flag}: expected a JSON object, got {type(parsed).__name__}")
        raise typer.Exit(code=1)
    return parsed


def _resolve_null(value: str) -> str | None:
    """Treat the literal string 'null' as None for move flags."""
    return None if value.lower() == "null" else value


# Sentinel for "do not touch" on tri-state CLI flags (e.g. --package-id).
_UNSET: Any = object()


async def _put_merge_partial(
    c: IrisClient, kind_path: str, entity_id: str,
    partial: dict[str, Any], updatable_fields: tuple[str, ...],
) -> dict[str, Any]:
    """GET-then-merge-then-PUT, mirroring the MCP update_* helper.

    The backend PUT does full-replace, so partial updates need a merge
    pass first. Costs one extra GET per update.

    Versioned entities (elements / diagrams / packages) require an
    ``If-Match`` header carrying the current version — backend rejects
    without it (HTTP 428). We inject it from the GET response when
    ``current_version`` is present; unversioned endpoints (collections,
    sets) omit the field and don't require the header.
    """
    current_resp = await c._request("GET", f"/api/{kind_path}/{entity_id}")
    current = current_resp.json()
    body: dict[str, Any] = {}
    for field in updatable_fields:
        if field in partial and partial[field] is not None:
            body[field] = partial[field]
        elif field in current:
            body[field] = current[field]
    headers: dict[str, str] | None = None
    if "current_version" in current:
        headers = {"If-Match": str(current["current_version"])}
    resp = await c._request(
        "PUT", f"/api/{kind_path}/{entity_id}", json=body, headers=headers,
    )
    return resp.json()


# ── iris create ────────────────────────────────────────────────────────────


@create_app.command("collection")
def create_collection_cmd(
    name: str = typer.Option(..., "--name"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new Collection."""
    async def _do() -> Any:
        async with _client() as c:
            return await c.create_collection(name=name, description=description)
    output.print_json(_run(_do()))


@create_app.command("set")
def create_set_cmd(
    name: str = typer.Option(..., "--name"),
    collection_id: str | None = typer.Option(None, "--collection-id"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new Set (optionally nested under a collection)."""
    async def _do() -> Any:
        async with _client() as c:
            return await c.create_set(
                name=name, collection_id=collection_id, description=description,
            )
    output.print_json(_run(_do()))


@create_app.command("package")
def create_package_cmd(
    name: str = typer.Option(..., "--name"),
    set_id: str | None = typer.Option(None, "--set-id"),
    parent_package_id: str | None = typer.Option(None, "--parent-package-id"),
    description: str | None = typer.Option(None, "--description"),
    metadata_json: str | None = typer.Option(
        None, "--metadata-json", help="Metadata as a JSON object string.",
    ),
) -> None:
    """Create a new Package."""
    metadata = _parse_json_opt(metadata_json, "--metadata-json")

    async def _do() -> Any:
        async with _client() as c:
            return await c.create_package(
                name=name, set_id=set_id, parent_package_id=parent_package_id,
                description=description, metadata=metadata,
            )
    output.print_json(_run(_do()))


@create_app.command("element")
def create_element_cmd(
    name: str = typer.Option(..., "--name"),
    element_type: str = typer.Option(..., "--element-type"),
    set_id: str | None = typer.Option(None, "--set-id"),
    package_id: str | None = typer.Option(
        None, "--package-id",
        help="Optional package membership for the new element (ADR-184).",
    ),
    notation: str | None = typer.Option(None, "--notation"),
    description: str | None = typer.Option(None, "--description"),
    data_json: str | None = typer.Option(None, "--data-json"),
    metadata_json: str | None = typer.Option(None, "--metadata-json"),
) -> None:
    """Create a standalone Element in a set's element pool.

    For drawing elements onto a diagram in one step, use
    `iris diagrams ...` flows or the API/MCP `apply_diagram_creation`
    tool instead.
    """
    body: dict[str, Any] = {
        "element_type": element_type,
        "name": name,
    }
    if set_id is not None:
        body["set_id"] = set_id
    if package_id is not None:
        body["package_id"] = package_id
    if notation is not None:
        body["notation"] = notation
    if description is not None:
        body["description"] = description
    data = _parse_json_opt(data_json, "--data-json")
    if data is not None:
        body["data"] = data
    metadata = _parse_json_opt(metadata_json, "--metadata-json")
    if metadata is not None:
        body["metadata"] = metadata

    async def _do() -> Any:
        async with _client() as c:
            resp = await c._request("POST", "/api/elements", json=body)
            return resp.json()
    output.print_json(_run(_do()))


@create_app.command("diagram")
def create_diagram_cmd(
    name: str = typer.Option(..., "--name"),
    diagram_type: str = typer.Option(..., "--diagram-type"),
    notation: str | None = typer.Option(None, "--notation"),
    set_id: str | None = typer.Option(None, "--set-id"),
    parent_package_id: str | None = typer.Option(None, "--parent-package-id"),
    description: str | None = typer.Option(None, "--description"),
    data_json: str | None = typer.Option(
        None, "--data-json", help="Canvas data as a JSON object string.",
    ),
) -> None:
    """Create a new Diagram."""
    data = _parse_json_opt(data_json, "--data-json")

    async def _do() -> Any:
        async with _client() as c:
            return await c.create_diagram(
                name=name, diagram_type=diagram_type, notation=notation,
                set_id=set_id, parent_package_id=parent_package_id,
                description=description, data=data,
            )
    output.print_json(_run(_do()))


# ── iris update ────────────────────────────────────────────────────────────

_COLLECTION_UPDATE_FIELDS = (
    "name", "description", "thumbnail_source", "thumbnail_diagram_id",
    "system_prompt", "mcp_system_context",
)
_SET_METADATA_FIELDS = (
    "name", "description", "thumbnail_source", "thumbnail_diagram_id",
    "system_prompt", "mcp_system_context",
)
_PACKAGE_UPDATE_FIELDS = ("name", "description", "metadata")
_DIAGRAM_UPDATE_FIELDS = ("name", "description", "data", "metadata", "change_summary")
_ELEMENT_UPDATE_FIELDS = ("name", "description", "data", "package_id")


@update_app.command("collection")
def update_collection_cmd(
    collection_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
    system_prompt: str | None = typer.Option(None, "--system-prompt"),
    mcp_system_context: str | None = typer.Option(None, "--mcp-system-context"),
    thumbnail_source: str | None = typer.Option(None, "--thumbnail-source"),
    thumbnail_diagram_id: str | None = typer.Option(None, "--thumbnail-diagram-id"),
) -> None:
    """Update a Collection's metadata (partial — GET-then-merge-then-PUT)."""
    partial = {
        "name": name, "description": description,
        "system_prompt": system_prompt,
        "mcp_system_context": mcp_system_context,
        "thumbnail_source": thumbnail_source,
        "thumbnail_diagram_id": thumbnail_diagram_id,
    }

    async def _do() -> Any:
        async with _client() as c:
            return await _put_merge_partial(
                c, "collections", collection_id, partial, _COLLECTION_UPDATE_FIELDS,
            )
    output.print_json(_run(_do()))


@update_app.command("set")
def update_set_cmd(
    set_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
    system_prompt: str | None = typer.Option(None, "--system-prompt"),
    mcp_system_context: str | None = typer.Option(None, "--mcp-system-context"),
    thumbnail_source: str | None = typer.Option(None, "--thumbnail-source"),
    thumbnail_diagram_id: str | None = typer.Option(None, "--thumbnail-diagram-id"),
) -> None:
    """Update a Set's metadata. To move a set between collections, use
    `iris move set` instead — this command deliberately excludes
    collection_id."""
    partial = {
        "name": name, "description": description,
        "system_prompt": system_prompt,
        "mcp_system_context": mcp_system_context,
        "thumbnail_source": thumbnail_source,
        "thumbnail_diagram_id": thumbnail_diagram_id,
    }

    async def _do() -> Any:
        async with _client() as c:
            return await _put_merge_partial(
                c, "sets", set_id, partial, _SET_METADATA_FIELDS,
            )
    output.print_json(_run(_do()))


@update_app.command("package")
def update_package_cmd(
    package_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
    metadata_json: str | None = typer.Option(None, "--metadata-json"),
) -> None:
    """Update a Package's metadata."""
    partial = {
        "name": name, "description": description,
        "metadata": _parse_json_opt(metadata_json, "--metadata-json"),
    }

    async def _do() -> Any:
        async with _client() as c:
            return await _put_merge_partial(
                c, "packages", package_id, partial, _PACKAGE_UPDATE_FIELDS,
            )
    output.print_json(_run(_do()))


@update_app.command("diagram")
def update_diagram_cmd(
    diagram_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
    data_json: str | None = typer.Option(None, "--data-json"),
    metadata_json: str | None = typer.Option(None, "--metadata-json"),
    change_summary: str | None = typer.Option(None, "--change-summary"),
) -> None:
    """Update a Diagram. Versioned — every successful update increments
    current_version. Use `iris move diagram` to re-parent."""
    partial = {
        "name": name, "description": description,
        "data": _parse_json_opt(data_json, "--data-json"),
        "metadata": _parse_json_opt(metadata_json, "--metadata-json"),
        "change_summary": change_summary,
    }

    async def _do() -> Any:
        async with _client() as c:
            return await _put_merge_partial(
                c, "diagrams", diagram_id, partial, _DIAGRAM_UPDATE_FIELDS,
            )
    output.print_json(_run(_do()))


@update_app.command("element")
def update_element_cmd(
    element_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
    data_json: str | None = typer.Option(None, "--data-json"),
    package_id: str | None = typer.Option(
        None, "--package-id",
        help=(
            "Set or clear the element's package membership. Pass a "
            "UUID to set, the literal 'null' to clear, or omit to leave "
            "unchanged (ADR-184). Cannot move elements between diagrams "
            "(ADR-178 invariant)."
        ),
    ),
) -> None:
    """Update an Element. Note: elements cannot be moved between
    diagrams — they travel with their parent diagram (ADR-178 invariant)."""
    partial: dict[str, Any] = {
        "name": name, "description": description,
        "data": _parse_json_opt(data_json, "--data-json"),
    }
    # package_id is tri-state at the PUT body level: include the key to
    # set (string) or clear (null), omit to leave untouched. The
    # _put_merge_partial helper strips None so we wire package_id by
    # hand.
    raw_package_id = _resolve_null(package_id) if package_id is not None else _UNSET

    async def _do() -> Any:
        async with _client() as c:
            # Build the body from the GET-then-merge path, then graft
            # package_id on if the user passed --package-id.
            current_resp = await c._request("GET", f"/api/elements/{element_id}")
            current = current_resp.json()
            body: dict[str, Any] = {}
            for field in ("name", "description", "data"):
                if field in partial and partial[field] is not None:
                    body[field] = partial[field]
                elif field in current:
                    body[field] = current[field]
            if raw_package_id is not _UNSET:
                body["package_id"] = raw_package_id
            headers = {"If-Match": str(current.get("current_version", 1))}
            resp = await c._request(
                "PUT", f"/api/elements/{element_id}", json=body, headers=headers,
            )
            return resp.json()
    output.print_json(_run(_do()))


# ── iris move ──────────────────────────────────────────────────────────────


@move_app.command("diagram")
def move_diagram_cmd(
    diagram_id: str = typer.Argument(...),
    to_package: str = typer.Option(
        ..., "--to-package",
        help="Target package id, or `null` to move to set root.",
    ),
) -> None:
    """Re-parent a diagram within its current set."""
    target = _resolve_null(to_package)

    async def _do() -> Any:
        async with _client() as c:
            resp = await c._request(
                "PUT", f"/api/diagrams/{diagram_id}/parent",
                json={"parent_package_id": target},
            )
            return resp.json()
    output.print_json(_run(_do()))


@move_app.command("package")
def move_package_cmd(
    package_id: str = typer.Argument(...),
    to_parent: str = typer.Option(
        ..., "--to-parent",
        help="Target parent package id, or `null` to move to set root.",
    ),
) -> None:
    """Re-parent a package within its current set (cycle-checked)."""
    target = _resolve_null(to_parent)

    async def _do() -> Any:
        async with _client() as c:
            resp = await c._request(
                "PUT", f"/api/packages/{package_id}/parent",
                json={"parent_package_id": target},
            )
            return resp.json()
    output.print_json(_run(_do()))


_SET_UPDATE_FIELDS = (
    "name", "description", "thumbnail_source", "thumbnail_diagram_id",
    "collection_id", "system_prompt", "mcp_system_context",
)


@move_app.command("set")
def move_set_cmd(
    set_id: str = typer.Argument(...),
    to_collection: str = typer.Option(
        ..., "--to-collection",
        help="Target collection id, or `null` to un-group.",
    ),
) -> None:
    """Move a set to a different (or no) collection. Preserves other
    metadata."""
    target = _resolve_null(to_collection)

    async def _do() -> Any:
        async with _client() as c:
            current_resp = await c._request("GET", f"/api/sets/{set_id}")
            current = current_resp.json()
            body: dict[str, Any] = {}
            for field in _SET_UPDATE_FIELDS:
                if field == "collection_id":
                    body["collection_id"] = target
                elif field in current:
                    body[field] = current[field]
            resp = await c._request("PUT", f"/api/sets/{set_id}", json=body)
            return resp.json()
    output.print_json(_run(_do()))


# ── iris render ────────────────────────────────────────────────────────────


def _write_or_print_artefact(
    meta: dict[str, Any], out: Path | None, body_bytes: bytes | None,
) -> None:
    if out is not None and body_bytes is not None:
        out.write_bytes(body_bytes)
        typer.echo(
            f"Wrote {len(body_bytes)} bytes to {out} "
            f"(artefact_id={meta.get('id')})",
        )
    else:
        output.print_json(meta)


@render_app.command("diagram")
def render_diagram_cmd(
    diagram_id: str = typer.Argument(...),
    format: str = typer.Option(..., "--format", help="md, docx, or pdf"),
    out: Path | None = typer.Option(
        None, "-o", "--output",
        help="If provided, download artefact bytes to this path. Otherwise print metadata.",
    ),
) -> None:
    """Render a diagram to md/docx/pdf and store as an Iris artefact."""
    async def _do() -> tuple[dict[str, Any], bytes | None]:
        async with _client() as c:
            resp = await c._request(
                "POST", f"/api/export/diagram/{diagram_id}",
                json={"format": format},
            )
            meta = resp.json()
            body_bytes: bytes | None = None
            if out is not None:
                got = await c._request(
                    "GET", f"/api/artefacts/{meta['id']}",
                )
                body_bytes = got.content
            return meta, body_bytes

    meta, body = _run(_do())
    _write_or_print_artefact(meta, out, body)


@render_app.command("markdown")
def render_markdown_cmd(
    title: str = typer.Option(..., "--title"),
    format: str = typer.Option(..., "--format", help="md, docx, or pdf"),
    input_file: Path | None = typer.Option(
        None, "--input",
        help="Read markdown source from this file. Reads stdin if omitted.",
    ),
    out: Path | None = typer.Option(
        None, "-o", "--output",
        help="If provided, download artefact bytes to this path. Otherwise print metadata.",
    ),
) -> None:
    """Render ad-hoc markdown to md/docx/pdf and store as an Iris
    artefact. Reads markdown source from --input or stdin."""
    if input_file is not None:
        source = input_file.read_text(encoding="utf-8")
    else:
        source = sys.stdin.read()

    async def _do() -> tuple[dict[str, Any], bytes | None]:
        async with _client() as c:
            resp = await c._request(
                "POST", "/api/export/markdown",
                json={"markdown": source, "title": title, "format": format},
            )
            meta = resp.json()
            body_bytes: bytes | None = None
            if out is not None:
                got = await c._request(
                    "GET", f"/api/artefacts/{meta['id']}",
                )
                body_bytes = got.content
            return meta, body_bytes

    meta, body = _run(_do())
    _write_or_print_artefact(meta, out, body)


if __name__ == "__main__":
    app()
