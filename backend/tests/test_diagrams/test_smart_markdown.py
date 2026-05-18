"""Tests for the Smart Markdown resolver (v6.14.0, ADR-205, issue #185).

The resolver walks a markdown source string for inline reference tokens
``{{<entity-type>:<id>:<field-spec>}}`` and substitutes the resolved
entity field. Unresolvable tokens render as ``~~{{...}}~~`` so the user
sees the failure rather than silently dropping it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.diagrams.smart_markdown import compute_smart_markdown_content
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def context(app_config: AppConfig) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        await c.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        resp = await c.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        yield c, db_manager, headers
    await db_manager.close()


async def _create_set(c: httpx.AsyncClient, h: dict[str, str], name: str = "S") -> str:
    r = await c.post("/api/sets", json={"name": name}, headers=h)
    assert r.status_code == 201
    return r.json()["id"]


async def _create_element(
    c: httpx.AsyncClient, h: dict[str, str], set_id: str, *,
    name: str, description: str | None = None, data: dict | None = None,
) -> str:
    body: dict = {"name": name, "element_type": "application", "set_id": set_id}
    if description is not None:
        body["description"] = description
    if data is not None:
        body["data"] = data
    r = await c.post("/api/elements", json=body, headers=h)
    assert r.status_code == 201
    return r.json()["id"]


async def _create_smart_markdown_diagram(
    c: httpx.AsyncClient, h: dict[str, str], set_id: str, source: str,
) -> str:
    r = await c.post(
        "/api/diagrams",
        json={
            "name": "SMD",
            "set_id": set_id,
            "diagram_type": "smart_markdown",
            "notation": "markdown",
            "data": {"markdown_source": source},
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_resolves_element_name(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h, "S")
    eid = await _create_element(c, h, set_id, name="Pork mince")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"Buy some {{{{element:{eid}:name}}}} today.",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert "Buy some Pork mince today." == rendered


@pytest.mark.asyncio
async def test_resolves_element_description(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X", description="lean cut")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"Note: {{{{element:{eid}:description}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert "Note: lean cut" == rendered


@pytest.mark.asyncio
async def test_resolves_element_attr(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="Pork mince", data={"Unit": "g"},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"500{{{{element:{eid}:attr:Unit}}}} {{{{element:{eid}:name}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert "500g Pork mince" == rendered


@pytest.mark.asyncio
async def test_missing_element_renders_strikethrough(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, "{{element:no-such-id:name}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == "~~{{element:no-such-id:name}}~~"


@pytest.mark.asyncio
async def test_missing_attr_renders_strikethrough(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="E", data={"Unit": "g"})
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:Missing}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{{{{element:{eid}:attr:Missing}}}}~~"


@pytest.mark.asyncio
async def test_attr_on_non_element_renders_strikethrough(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{set:{set_id}:attr:Anything}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{{{{set:{set_id}:attr:Anything}}}}~~"


@pytest.mark.asyncio
async def test_resolves_set_name(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h, "Groceries")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"In set {{{{set:{set_id}:name}}}}.",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == "In set Groceries."


@pytest.mark.asyncio
async def test_multiple_tokens_one_line(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    e1 = await _create_element(c, h, set_id, name="A", data={"Unit": "g"})
    e2 = await _create_element(c, h, set_id, name="B", data={"Unit": "kg"})
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"- 100{{{{element:{e1}:attr:Unit}}}} {{{{element:{e1}:name}}}}\n"
        f"- 2{{{{element:{e2}:attr:Unit}}}} {{{{element:{e2}:name}}}}\n",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == "- 100g A\n- 2kg B\n"


@pytest.mark.asyncio
async def test_empty_source_returns_placeholder(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    diag_id = await _create_smart_markdown_diagram(c, h, set_id, "")
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered.startswith("_No content yet._") or rendered == "_No content yet._"


@pytest.mark.asyncio
async def test_no_tokens_returns_source_unchanged(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, "# Title\n\nPlain markdown with no tokens.",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == "# Title\n\nPlain markdown with no tokens."


@pytest.mark.asyncio
async def test_get_diagram_populates_data_content(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-187 dispatch — `_maybe_synthesise_content` overlays
    `data.content` on GET for smart_markdown diagrams."""
    c, _db, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="Foo")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"Hi {{{{element:{eid}:name}}}}!",
    )
    g = await c.get(f"/api/diagrams/{diag_id}", headers=h)
    assert g.status_code == 200
    body = g.json()
    assert body["data"]["content"] == "Hi Foo!"
