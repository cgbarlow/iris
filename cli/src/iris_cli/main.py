"""Typer entry point for the `iris` CLI (ADR-130 / SPEC-130-A).

Commands are grouped by entity / concern. All async calls to the backend
route through a single `iris_client.IrisClient` instance configured via
`iris_cli.config.load`.
"""

from __future__ import annotations

import asyncio
import getpass
import socket
import sys
from pathlib import Path
from typing import Any

import httpx
import typer
from iris_client import IrisAuthError, IrisClient, IrisClientError

from iris_cli import config as cfg
from iris_cli import output

app = typer.Typer(
    name="iris",
    help="Command-line interface for Iris (read-only + AI).",
    no_args_is_help=True,
)

# --- Sub-apps per entity group ----------------------------------------------

diagrams_app = typer.Typer(help="Diagram commands.", no_args_is_help=True)
elements_app = typer.Typer(help="Element commands.", no_args_is_help=True)
packages_app = typer.Typer(help="Package commands.", no_args_is_help=True)
sets_app = typer.Typer(help="Set commands.", no_args_is_help=True)
collections_app = typer.Typer(help="Collection commands.", no_args_is_help=True)
export_app = typer.Typer(help="Export entities as JSON or Markdown.", no_args_is_help=True)
conversations_app = typer.Typer(help="Conversation commands.", no_args_is_help=True)

app.add_typer(diagrams_app, name="diagrams")
app.add_typer(elements_app, name="elements")
app.add_typer(packages_app, name="packages")
app.add_typer(sets_app, name="sets")
app.add_typer(collections_app, name="collections")
app.add_typer(export_app, name="export")
app.add_typer(conversations_app, name="conversations")


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
) -> None:
    """Log in with username+password, mint a PAT, and save it to ~/.config/iris/config.toml."""
    final_url = url or state.url or cfg.DEFAULT_URL
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

    saved_to = _run(_do())
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
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(50, "--page-size", min=1, max=200),
) -> None:
    async def _do() -> list[Any]:
        async with _client() as c:
            return await c.list_elements(
                set_id=set_id, page=page, page_size=page_size,
            )

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


if __name__ == "__main__":
    app()
