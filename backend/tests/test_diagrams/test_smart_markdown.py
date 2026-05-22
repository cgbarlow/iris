"""Tests for the Smart Markdown resolver (v6.14.0, ADR-205, issue #185).

The resolver walks a markdown source string for inline reference tokens
``{{<entity-type>:<id>:<field-spec>}}`` and substitutes the resolved
entity field. Unresolvable tokens render as ``~~{{...}}~~`` so the user
sees the failure rather than silently dropping it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import httpx
import pytest


# ADR-209 (v6.17.0): resolved entity-field values are wrapped in
# iris:// markdown links so they're clickable and tooltip-bearing in
# MarkdownView. Existing tests assert the pre-wrap content — this helper
# strips the link wrapper so those assertions keep working without
# rewriting each one. New ADR-209 tests below assert the wrapper itself.
_LINK_RE = re.compile(r'\[([^\]]*)\]\(iris://[^)]+\)')


def _unwrap_iris_links(s: str) -> str:
    """Strip `[text](iris://...)` wrappers, returning just the text."""
    return _LINK_RE.sub(r'\1', s)

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
    assert _unwrap_iris_links(rendered) == "Buy some Pork mince today."


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
    assert _unwrap_iris_links(rendered) == "Note: lean cut"


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
    assert _unwrap_iris_links(rendered) == "500g Pork mince"


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
    assert _unwrap_iris_links(rendered) == "In set Groceries."


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
    assert _unwrap_iris_links(rendered) == "- 100g A\n- 2kg B\n"


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
    assert _unwrap_iris_links(body["data"]["content"]) == "Hi Foo!"


# ──────────────────────────────────────────────────────────────────
# ADR-206 / v6.15.0: nested-path drill resolution
# ──────────────────────────────────────────────────────────────────

_RECIPE_ATTRS = [
    {"name": "Unit", "type": "g", "scope": "Public", "notes": ""},
    {"name": "Products", "type": "WW Pork Rump", "scope": "Public", "notes": ""},
    {"name": "Preferred", "type": "WW Pork Fillet", "scope": "Public", "notes": ""},
]


@pytest.mark.asyncio
async def test_named_lookup_in_array_of_dicts(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: `attr:attributes/Unit/type` resolves via name-match
    in the array-of-dicts, then takes the named sub-field."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="Pork mince", data={"attributes": _RECIPE_ATTRS},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"500{{{{element:{eid}:attr:attributes/Unit/type}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "500g"


@pytest.mark.asyncio
async def test_numeric_index_in_list(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: `attr:tags/0` indexes a list positionally."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E", data={"tags": ["alpha", "beta", "gamma"]},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:tags/1}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "beta"


@pytest.mark.asyncio
async def test_numeric_index_into_named_array_still_works(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: numeric segments index even when the array's items
    have a `name` field — explicit index wins."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E", data={"attributes": _RECIPE_ATTRS},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:attributes/0/type}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "g"  # first item is Unit, its type is "g"


@pytest.mark.asyncio
async def test_missing_path_segment_renders_strikethrough(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: missing intermediate or terminal segment → fail-loud."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E", data={"attributes": _RECIPE_ATTRS},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:attributes/Missing/type}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{{{{element:{eid}:attr:attributes/Missing/type}}}}~~"


@pytest.mark.asyncio
async def test_legacy_single_key_on_container_renders_literal(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206 backward-compat: existing v6.14.x tokens like
    `attr:attributes` that land on a list still render the JSON
    literal (the v6.14.0 behaviour). New tokens drill further."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E", data={"attributes": _RECIPE_ATTRS},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:attributes}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    # not strikethrough — we render some kind of stringification
    assert not rendered.startswith("~~"), rendered
    assert "Unit" in rendered  # the list literal contains the name


@pytest.mark.asyncio
async def test_dict_key_matches_before_named_lookup(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: at a dict node, a matching key always wins.
    Named-lookup is only attempted on list nodes."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E",
        data={"profile": {"name": "Alice", "role": "admin"}},
    )
    # `profile/name` is a dict key match, not a named-array lookup.
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:profile/name}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "Alice"


@pytest.mark.asyncio
async def test_deeply_nested_path(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: 4+ segments walking dict → list_of_named → dict → primitive."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E",
        data={
            "groups": [
                {"name": "alpha", "members": [{"name": "a1", "level": 7}]},
                {"name": "beta", "members": [{"name": "b1", "level": 3}]},
            ],
        },
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:groups/beta/members/0/level}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "3"


# ──────────────────────────────────────────────────────────────────
# ADR-209 / v6.17.0: entity-reference values wrapped in iris:// links
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_element_name_emits_iris_link(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-209: resolved element-name values are wrapped in a markdown
    link with the entity name as the tooltip title so MarkdownView
    can render them as clickable links with hover tooltips."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="Pork mince")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:name}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'[Pork mince](iris://element/{eid} "Pork mince")' == rendered


@pytest.mark.asyncio
async def test_element_attr_value_wrapped_with_name_tooltip(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-209: even non-name values (e.g. attribute strings) link back
    to the parent entity, with the entity name as the tooltip title."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="Pork mince", data={"Unit": "g"},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:Unit}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'[g](iris://element/{eid} "Pork mince")' == rendered


@pytest.mark.asyncio
async def test_set_name_wrapped_in_iris_set_link(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-209: set references use iris://set/<id> so MarkdownView routes
    the click to /sets/<id>."""
    c, db_manager, h = context
    set_id = await _create_set(c, h, "Groceries")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"In {{{{set:{set_id}:name}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'iris://set/{set_id}' in rendered
    assert '[Groceries]' in rendered


# ──────────────────────────────────────────────────────────────────
# ADR-209 / v6.17.0: image tokens
# ──────────────────────────────────────────────────────────────────


_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01]\xcc\x86\xcf"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def _upload_image_for_test(c: httpx.AsyncClient, h: dict[str, str]) -> str:
    import io
    r = await c.post(
        "/api/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_image_token_original_renders_img_tag(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-209: `{{image:<id>}}` renders an <img> tag at original size."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    image_id = await _upload_image_for_test(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"Before {{{{image:{image_id}}}}} after",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'<img src="/api/images/{image_id}" alt="">' in rendered
    assert rendered.startswith("Before ")
    assert rendered.endswith(" after")


@pytest.mark.asyncio
@pytest.mark.parametrize("sizing,style", [
    ("width:50%", 'style="width:50%"'),
    ("width:300px", 'style="width:300px"'),
    ("height:25%", 'style="height:25%"'),
    ("height:200px", 'style="height:200px"'),
])
async def test_image_token_with_sizing(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
    sizing: str, style: str,
) -> None:
    """ADR-209: sizing directives emit style attributes."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    image_id = await _upload_image_for_test(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{image:{image_id}:{sizing}}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'<img src="/api/images/{image_id}" {style} alt="">' == rendered.strip()


@pytest.mark.asyncio
async def test_image_token_original_explicit(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-209: `{{image:<id>:original}}` is the same as `{{image:<id>}}`."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    image_id = await _upload_image_for_test(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{image:{image_id}:original}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'<img src="/api/images/{image_id}" alt="">' == rendered.strip()


@pytest.mark.asyncio
async def test_missing_image_renders_strikethrough(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, "{{image:00000000-0000-0000-0000-000000000000:width:50%}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == "~~{{image:00000000-0000-0000-0000-000000000000:width:50%}}~~"


@pytest.mark.asyncio
async def test_image_token_invalid_sizing_falls_back_to_original(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """A token with a malformed sizing directive still renders the image —
    just without style. The image itself is valid; only the directive
    was unparseable."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    image_id = await _upload_image_for_test(c, h)
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{image:{image_id}:gibberish}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert f'<img src="/api/images/{image_id}" alt="">' == rendered.strip()


@pytest.mark.asyncio
async def test_primitive_then_more_segments_renders_strikethrough(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-206: trying to drill past a primitive is unresolvable."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="E", data={"unit": "g"},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id, f"{{{{element:{eid}:attr:unit/extra}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{{{{element:{eid}:attr:unit/extra}}}}~~"


# ─────────────────────────────────────────────────────────────────────
# ADR-210: token =value overrides (per-use values + fillable slots)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_override_value_replaces_stored_attr(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: `attr:path=500` resolves to "500" regardless of stored value."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="Pork mince", data={"Quantity": "5"},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:Quantity=500}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "500"


@pytest.mark.asyncio
async def test_override_value_with_blank_stored_attr(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: override works even when stored attribute is absent."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X")  # no Quantity attr
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:Quantity=500}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "500"


@pytest.mark.asyncio
async def test_empty_override_renders_strikethrough_fillable_slot(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: `attr:path=` (empty override) is the fillable-slot marker."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X")
    token = f"{{{{element:{eid}:attr:Quantity=}}}}"
    diag_id = await _create_smart_markdown_diagram(c, h, set_id, token)
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{token}~~"


@pytest.mark.asyncio
async def test_empty_override_strikethrough_even_with_stored_value(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: empty override does NOT fall through to stored value.
    The author explicitly chose "this is a slot to fill" — respect that."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X", data={"Q": "preset"})
    token = f"{{{{element:{eid}:attr:Q=}}}}"
    diag_id = await _create_smart_markdown_diagram(c, h, set_id, token)
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{token}~~"


@pytest.mark.asyncio
async def test_override_on_name_field(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: override works on `name` field too, not just attr."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="Pork mince")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:name=Custom Label}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "Custom Label"


@pytest.mark.asyncio
async def test_override_on_package_name(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: override works on any non-element entity's name/description."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    r = await c.post(
        "/api/packages",
        json={"name": "Pantry", "set_id": set_id},
        headers=h,
    )
    assert r.status_code == 201
    pid = r.json()["id"]
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{package:{pid}:name=Aisle 7}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "Aisle 7"


@pytest.mark.asyncio
async def test_override_value_containing_equals_signs(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: split on FIRST `=` — values can contain `=`."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:foo=k=v=w}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "k=v=w"


@pytest.mark.asyncio
async def test_override_value_with_markdown_brackets_is_escaped(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: override values pass through the same markdown-link-text
    escape as stored values (so `[`/`]` don't break the iris:// wrapper)."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X")
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:x=hello [world]}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    # Wrapped: [hello \[world\]](iris://element/<id> "X")
    assert "[hello \\[world\\]]" in rendered
    assert f"iris://element/{eid}" in rendered


@pytest.mark.asyncio
async def test_override_on_deleted_entity_strikes_through(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: dangling reference takes precedence over override —
    a deleted element renders as strikethrough even with an override."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(c, h, set_id, name="X")
    # Soft-delete the element (optimistic locking requires If-Match)
    r = await c.delete(
        f"/api/elements/{eid}",
        headers={**h, "If-Match": "1"},
    )
    assert r.status_code in (200, 204), r.text
    token = f"{{{{element:{eid}:attr:Quantity=500}}}}"
    diag_id = await _create_smart_markdown_diagram(c, h, set_id, token)
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert rendered == f"~~{token}~~"


@pytest.mark.asyncio
async def test_no_override_existing_behaviour_preserved(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: tokens without `=` resolve to stored value as before."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="X", data={"Unit": "g"},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:Unit}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "g"


@pytest.mark.asyncio
async def test_override_alongside_unoverridden_in_one_diagram(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: real-world recipe line composes override + stored + stored."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="Pork mince", data={"Unit": "g"},
    )
    src = (
        f"- {{{{element:{eid}:attr:Quantity=500}}}}"
        f" {{{{element:{eid}:attr:Unit}}}}"
        f" {{{{element:{eid}:name}}}}"
    )
    diag_id = await _create_smart_markdown_diagram(c, h, set_id, src)
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "- 500 g Pork mince"


@pytest.mark.asyncio
async def test_override_on_attr_path_with_nested_segments(
    context: tuple[httpx.AsyncClient, DatabaseManager, dict[str, str]],
) -> None:
    """ADR-210: works on multi-segment attribute paths too (ADR-206 grammar)."""
    c, db_manager, h = context
    set_id = await _create_set(c, h)
    eid = await _create_element(
        c, h, set_id, name="X",
        data={"attributes": [{"name": "Quantity", "type": ""}]},
    )
    diag_id = await _create_smart_markdown_diagram(
        c, h, set_id,
        f"{{{{element:{eid}:attr:attributes/Quantity/type=2.5}}}}",
    )
    rendered = await compute_smart_markdown_content(db_manager.main_db, diag_id)
    assert _unwrap_iris_links(rendered) == "2.5"
