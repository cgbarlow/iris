"""Element template markdown stamps (ADR-211, v6.19.0, issue #211).

Covers:
- markdown_stamp create + update on /api/element-templates.
- substitute_self() unit behaviour.
- GET /api/element-templates/stamps?element_id=X with scope and
  element_type filtering.
- The five seeded global stamps are present after migrations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.element_templates.service import substitute_self
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
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_set(c: httpx.AsyncClient, h: dict, name: str = "S") -> str:
    r = await c.post("/api/sets", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_element(
    c: httpx.AsyncClient, h: dict, *, set_id: str,
    name: str = "E", element_type: str = "class",
    data: dict | None = None,
) -> str:
    body: dict = {
        "name": name, "element_type": element_type, "set_id": set_id,
    }
    if data is not None:
        body["data"] = data
    r = await c.post(
        "/api/elements", json=body, headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _attrs(*names: str) -> dict:
    """Build an element.data shape with the named attributes (all blank type)."""
    return {
        "attributes": [
            {"name": n, "type": "", "scope": "Public",
             "notes": "", "lower_bound": "", "upper_bound": ""}
            for n in names
        ],
    }


# All five seeded global stamps reference these attributes in their
# bodies. Used by tests that need ALL seeded stamps to apply at once.
_ALL_SEEDED_ATTRS = _attrs(
    "Quantity", "Unit",          # Quantified item / Ingredient
    "Points",                    # Sized story
    "Hours",                     # Logged work
    "Amount", "Currency",        # Line item
    "Pages", "Author",           # Read entry
)


# ─────────────────────────────────────────────────────────────────────
# substitute_self() — pure function
# ─────────────────────────────────────────────────────────────────────


def test_substitute_self_single_token() -> None:
    out = substitute_self("Hello {{self:name}}.", "abc")
    assert out == "Hello {{element:abc:name}}."


def test_substitute_self_multiple_tokens() -> None:
    out = substitute_self(
        "{{self:attr:Q/type=}} {{self:attr:U/type}} {{self:name}}",
        "xyz",
    )
    assert out == (
        "{{element:xyz:attr:Q/type=}} "
        "{{element:xyz:attr:U/type}} "
        "{{element:xyz:name}}"
    )


def test_substitute_self_no_tokens() -> None:
    assert substitute_self("plain markdown", "abc") == "plain markdown"


def test_substitute_self_preserves_non_self_tokens() -> None:
    """Only `self` tokens are rewritten; other entity types pass through."""
    src = "{{self:name}} vs {{element:other-id:name}}"
    out = substitute_self(src, "abc")
    assert out == "{{element:abc:name}} vs {{element:other-id:name}}"


# ─────────────────────────────────────────────────────────────────────
# CRUD: create / update with markdown_stamp
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template_with_markdown_stamp_no_source(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Stamp only",
            "description": "no source element, just a stamp",
            "markdown_stamp": "{{self:name}}",
            "is_global": True,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["markdown_stamp"] == "{{self:name}}"
    assert body["source_element_id"] is None
    assert body["is_global"] is True


@pytest.mark.asyncio
async def test_create_rejects_empty_template(
    client: httpx.AsyncClient,
) -> None:
    """ADR-211: a template must have *some* content."""
    h = await _auth(client)
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Empty",
            "is_global": True,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert "at least one" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_with_direct_template_data(
    client: httpx.AsyncClient,
) -> None:
    """ADR-211: template_data can be supplied directly without a source."""
    h = await _auth(client)
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Blueprint",
            "template_data": {
                "element_type": "class",
                "data": {"attributes": [{"name": "X", "type": ""}]},
            },
            "is_global": True,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["template_data"]["element_type"] == "class"


@pytest.mark.asyncio
async def test_update_markdown_stamp(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    # create a stamp-only template
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Original",
            "markdown_stamp": "{{self:name}}",
            "is_global": True,
        },
        headers=h,
    )
    tid = r.json()["id"]
    # update the stamp
    r = await client.put(
        f"/api/element-templates/{tid}",
        json={"markdown_stamp": "{{self:attr:Q/type=}} {{self:name}}"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert (
        r.json()["markdown_stamp"]
        == "{{self:attr:Q/type=}} {{self:name}}"
    )


# ─────────────────────────────────────────────────────────────────────
# GET /api/element-templates/stamps?element_id=…
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stamps_endpoint_returns_seeded_globals_for_class_element(
    client: httpx.AsyncClient,
) -> None:
    """ADR-215: an element with *all* the attributes the seeded stamps
    reference in their bodies sees all five seeded stamps."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_ALL_SEEDED_ATTRS,
    )
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    assert r.status_code == 200, r.text
    names = sorted(s["name"] for s in r.json()["items"])
    # Five seeded global stamps all target element_type=class.
    assert names == [
        "Ingredient", "Line item", "Logged work",
        "Read entry", "Sized story",
    ]


@pytest.mark.asyncio
async def test_stamps_self_substituted_to_element_id(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, name="Pork mince", element_type="class",
        data=_attrs("Quantity", "Unit"),
    )
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    assert r.status_code == 200
    quantified = next(
        s for s in r.json()["items"] if s["name"] == "Ingredient"
    )
    # `self` is rewritten to `element:<eid>` in the returned stamp body.
    assert f"element:{eid}:attr:attributes/Quantity/type=" in (
        quantified["markdown_stamp"]
    )
    assert f"element:{eid}:name" in quantified["markdown_stamp"]
    assert "{{self:" not in quantified["markdown_stamp"]


@pytest.mark.asyncio
async def test_stamps_element_type_filter(
    client: httpx.AsyncClient,
) -> None:
    """Stamp template_data.element_type narrows applicability."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    # An element of element_type="component" should NOT see stamps that
    # the seed migration targeted at element_type="class".
    eid = await _create_element(
        client, h, set_id=set_id, element_type="component",
    )
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    assert r.status_code == 200
    assert r.json()["items"] == []


@pytest.mark.asyncio
async def test_stamps_set_scope_filter(
    client: httpx.AsyncClient,
) -> None:
    """A set-scoped stamp doesn't surface for elements in other sets."""
    h = await _auth(client)
    set_a = await _create_set(client, h, "A")
    set_b = await _create_set(client, h, "B")
    el_a = await _create_element(client, h, set_id=set_a)
    el_b = await _create_element(client, h, set_id=set_b)
    # Create a set-A-scoped stamp.
    await client.post(
        "/api/element-templates",
        json={
            "name": "A-only stamp",
            "markdown_stamp": "{{self:name}}",
            "set_id": set_a,
            "is_global": False,
        },
        headers=h,
    )
    # In set A: appears.
    r = await client.get(
        f"/api/element-templates/stamps?element_id={el_a}", headers=h,
    )
    names_a = [s["name"] for s in r.json()["items"]]
    assert "A-only stamp" in names_a
    # In set B: not visible.
    r = await client.get(
        f"/api/element-templates/stamps?element_id={el_b}", headers=h,
    )
    names_b = [s["name"] for s in r.json()["items"]]
    assert "A-only stamp" not in names_b


@pytest.mark.asyncio
async def test_stamps_missing_element_returns_empty_list(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.get(
        "/api/element-templates/stamps?"
        "element_id=00000000-0000-0000-0000-000000000000",
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["items"] == []


# ─────────────────────────────────────────────────────────────────────
# ADR-215 / SPEC-211-d: body-parsing attribute filter
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_body_filter_hides_stamp_when_required_attribute_missing(
    client: httpx.AsyncClient,
) -> None:
    """ADR-215: stamp body requires Points; element has only Quantity+Unit
    → stamp hidden."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_attrs("Quantity", "Unit"),
    )
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    names = sorted(s["name"] for s in r.json()["items"])
    # Sized story (Points), Logged work (Hours), Line item (Amount/Currency),
    # Read entry (Pages/Author) — all hidden. Only Quantified item shows.
    assert names == ["Ingredient"]


@pytest.mark.asyncio
async def test_body_filter_shows_stamp_when_all_required_attrs_present(
    client: httpx.AsyncClient,
) -> None:
    """Quantified item body needs Quantity + Unit; element has both → shown."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_attrs("Quantity", "Unit", "Products"),  # extras don't matter
    )
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    names = sorted(s["name"] for s in r.json()["items"])
    assert "Ingredient" in names


@pytest.mark.asyncio
async def test_body_filter_hides_stamp_when_required_attr_partial(
    client: httpx.AsyncClient,
) -> None:
    """Line item body requires Amount AND Currency; element has only Amount."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_attrs("Amount"),  # missing Currency
    )
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    names = [s["name"] for s in r.json()["items"]]
    assert "Line item" not in names


@pytest.mark.asyncio
async def test_body_trivial_stamp_applies_without_attrs(
    client: httpx.AsyncClient,
) -> None:
    """A stamp body that uses no `self:attr:` tokens (e.g. just `name`)
    passes the body filter trivially — applies to any matching-type
    element regardless of attribute set."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, element_type="class",
    )  # no attributes
    # Create a body-trivial stamp.
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Just the name",
            "markdown_stamp": "{{self:name}}",
            "is_global": True,
        },
        headers=h,
    )
    assert r.status_code == 201

    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    names = [s["name"] for s in r.json()["items"]]
    assert "Just the name" in names
    # The seeded stamps reference attributes → hidden from this element.
    assert "Ingredient" not in names


@pytest.mark.asyncio
async def test_body_filter_user_stamp_referencing_custom_attribute(
    client: httpx.AsyncClient,
) -> None:
    """A user-authored stamp body referencing a custom attribute applies
    only to elements that have that attribute."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    # Element WITH the custom attribute.
    eid_with = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_attrs("Difficulty"),
    )
    # Element WITHOUT the custom attribute.
    eid_without = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_attrs("OtherAttr"),
    )
    # Create the user stamp.
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Difficulty-rated",
            "markdown_stamp":
                "{{self:attr:attributes/Difficulty/type=}} - {{self:name}}",
            "is_global": True,
        },
        headers=h,
    )
    assert r.status_code == 201

    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid_with}", headers=h,
    )
    assert "Difficulty-rated" in [s["name"] for s in r.json()["items"]]

    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid_without}", headers=h,
    )
    assert "Difficulty-rated" not in [s["name"] for s in r.json()["items"]]


@pytest.mark.asyncio
async def test_body_filter_dedupes_same_attribute_referenced_twice(
    client: httpx.AsyncClient,
) -> None:
    """A stamp body referencing the same attribute twice — required set is
    deduplicated, behaviour identical to a single reference."""
    h = await _auth(client)
    set_id = await _create_set(client, h)
    eid = await _create_element(
        client, h, set_id=set_id, element_type="class",
        data=_attrs("Quantity"),
    )
    r = await client.post(
        "/api/element-templates",
        json={
            "name": "Double-quantity",
            "markdown_stamp":
                "{{self:attr:attributes/Quantity/type=}} "
                "{{self:attr:attributes/Quantity/notes}}",
            "is_global": True,
        },
        headers=h,
    )
    assert r.status_code == 201
    r = await client.get(
        f"/api/element-templates/stamps?element_id={eid}", headers=h,
    )
    assert "Double-quantity" in [s["name"] for s in r.json()["items"]]
