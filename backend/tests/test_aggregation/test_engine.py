"""Engine compute tests (ADR-212, SPEC-212-b)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.aggregation import engine as _engine
from app.aggregation.exceptions import (
    AggregationProfileNotFound,
    AggregationSourceNotFound,
)
from app.aggregation.profiles_service import (
    create_aggregation_profile,
)
from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
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
async def env(app_config: AppConfig) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager, dict]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        await c.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        resp = await c.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        h = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        yield c, db_manager, h
    await db_manager.close()


async def _create_set(c, h, name="S") -> str:
    r = await c.post("/api/sets", json={"name": name}, headers=h)
    assert r.status_code == 201
    return r.json()["id"]


async def _create_package(c, h, set_id, name) -> str:
    r = await c.post(
        "/api/packages",
        json={"name": name, "set_id": set_id},
        headers=h,
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_element(c, h, *, set_id, name, package_id=None, data=None) -> str:
    body = {
        "name": name, "element_type": "class", "set_id": set_id,
    }
    if data is not None:
        body["data"] = data
    if package_id is not None:
        body["package_id"] = package_id
    r = await c.post("/api/elements", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_smart_md(c, h, set_id, source, name="SMD", servings=None) -> str:
    data = {"markdown_source": source}
    if servings is not None:
        data["servings"] = servings
    r = await c.post(
        "/api/diagrams",
        json={
            "name": name, "set_id": set_id,
            "diagram_type": "smart_markdown",
            "notation": "markdown",
            "data": data,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


_ATTR_BLUEPRINT = {
    "attributes": [
        {"name": "Quantity", "type": "", "scope": "Public",
         "notes": "", "lower_bound": "", "upper_bound": ""},
        {"name": "Unit", "type": "g", "scope": "Public",
         "notes": "", "lower_bound": "", "upper_bound": ""},
    ],
}


# ─────────────────────────────────────────────────────────────────────
# Single-level walk
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_single_level_sum_one_element(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, dm, h = env
    set_id = await _create_set(c, h)
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince", data=_ATTR_BLUEPRINT,
    )
    diag_id = await _create_smart_md(
        c, h, set_id,
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}}",
    )
    # Profile: walk inner only, no bucket, group_by element.name
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Test single",
        description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.name",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}",
                "show_per_source_breakdown": False,
                "breakdown_format": "",
            },
        },
        is_default_for_set=False,
        created_by=None,
    )
    result = await _engine.run(
        dm.main_db,
        profile_id=profile["id"],
        source_diagram_id=diag_id,
    )
    assert "Pork mince: 500" in result.markdown
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_single_level_sum_same_element_twice(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Two references to the same element with same unit → summed."""
    c, dm, h = env
    set_id = await _create_set(c, h)
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince", data=_ATTR_BLUEPRINT,
    )
    source = (
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}} "
        f"{{{{element:{pork_id}:attr:attributes/Unit/type}}}}\n"
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}} "
        f"{{{{element:{pork_id}:attr:attributes/Unit/type}}}}"
    )
    diag_id = await _create_smart_md(c, h, set_id, source)
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Sum with bucket", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": "attributes/Unit/type",
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.name",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}{bucket_spaced}",
            },
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=diag_id,
    )
    # 500 + 500 = 1000 g
    assert "Pork mince: 1000 g" in result.markdown
    assert result.row_count == 1


# ─────────────────────────────────────────────────────────────────────
# Two-level walk + multiplier
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_two_level_walk_with_multiplier(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Meal plan referencing two recipes, each contributing 500 g of
    pork mince — recipe A scaled ×1.5 (diners=6, servings=4)."""
    c, dm, h = env
    set_id = await _create_set(c, h)
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince", data=_ATTR_BLUEPRINT,
    )
    rec_a = await _create_smart_md(
        c, h, set_id,
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}} "
        f"{{{{element:{pork_id}:attr:attributes/Unit/type}}}}",
        name="Recipe A", servings=4,
    )
    rec_b = await _create_smart_md(
        c, h, set_id,
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}} "
        f"{{{{element:{pork_id}:attr:attributes/Unit/type}}}}",
        name="Recipe B", servings=4,
    )
    # Meal plan: recipe A with Diners=6 override, recipe B with default 1
    meal_plan = await _create_smart_md(
        c, h, set_id,
        f"- {{{{diagram:{rec_a}:attr:attributes/Diners/type=6}}}}\n"
        f"- {{{{diagram:{rec_b}}}}}",
        name="Meal plan",
    )
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Two-level test", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                    "multiplier": {
                        "from_attribute_override": "attributes/Diners/type",
                        "divisor_from_diagram_data": "data.servings",
                        "default_multiplier": 1,
                    },
                },
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": "attributes/Unit/type",
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.name",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}{bucket_spaced}",
            },
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=meal_plan,
    )
    # A: 500 × (6/4) = 750; B: 500 × 1 = 500; total = 1250 g.
    assert "Pork mince: 1250 g" in result.markdown


# ─────────────────────────────────────────────────────────────────────
# Mixed buckets → two lines
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mixed_units_emit_two_lines(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Two different elements with different stored Units → two
    bucket-grouped lines (no cross-unit conversion per Q3)."""
    c, dm, h = env
    set_id = await _create_set(c, h)
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince",
        data={"attributes": [
            {"name": "Quantity", "type": "", "scope": "Public",
             "notes": "", "lower_bound": "", "upper_bound": ""},
            {"name": "Unit", "type": "g", "scope": "Public",
             "notes": "", "lower_bound": "", "upper_bound": ""},
        ]},
    )
    butter_id = await _create_element(
        c, h, set_id=set_id, name="Butter",
        data={"attributes": [
            {"name": "Quantity", "type": "", "scope": "Public",
             "notes": "", "lower_bound": "", "upper_bound": ""},
            {"name": "Unit", "type": "tbsp", "scope": "Public",
             "notes": "", "lower_bound": "", "upper_bound": ""},
        ]},
    )
    source = (
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}}\n"
        f"- {{{{element:{butter_id}:attr:attributes/Quantity/type=2}}}}"
    )
    diag_id = await _create_smart_md(c, h, set_id, source)
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Mixed buckets", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": "attributes/Unit/type",
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.name",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}{bucket_spaced}",
            },
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=diag_id,
    )
    # Two lines — one per element/unit pair; no cross-unit normalisation.
    assert "Pork mince: 500 g" in result.markdown
    assert "Butter: 2 tbsp" in result.markdown
    assert result.row_count == 2


# ─────────────────────────────────────────────────────────────────────
# group_by package_name
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_group_by_package_name(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, dm, h = env
    set_id = await _create_set(c, h)
    aisle_meat = await _create_package(c, h, set_id, "Meat & Poultry")
    aisle_produce = await _create_package(c, h, set_id, "Produce")
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince",
        package_id=aisle_meat, data=_ATTR_BLUEPRINT,
    )
    carrot_id = await _create_element(
        c, h, set_id=set_id, name="Carrot",
        package_id=aisle_produce, data=_ATTR_BLUEPRINT,
    )
    source = (
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}}\n"
        f"- {{{{element:{carrot_id}:attr:attributes/Quantity/type=3}}}}"
    )
    diag_id = await _create_smart_md(c, h, set_id, source)
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Group by aisle", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.package_name",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}",
            },
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=diag_id,
    )
    # Two ## groups, alpha-sorted: Meat & Poultry, Produce.
    md = result.markdown
    assert "## Meat & Poultry" in md
    assert "## Produce" in md
    assert md.index("## Meat & Poultry") < md.index("## Produce")
    assert "Pork mince: 500" in md
    assert "Carrot: 3" in md


# ─────────────────────────────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_missing_profile_raises(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    _, dm, _ = env
    with pytest.raises(AggregationProfileNotFound):
        await _engine.run(
            dm.main_db,
            profile_id="00000000-0000-0000-0000-000000000000",
            source_diagram_id="00000000-0000-0000-0000-000000000000",
        )


@pytest.mark.asyncio
async def test_run_missing_source_raises(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, dm, h = env
    set_id = await _create_set(c, h)
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Test missing-source", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "skip_blank_values": True,
                },
            },
            "output": {"line_format": "- {element.name}"},
        },
        is_default_for_set=False, created_by=None,
    )
    with pytest.raises(AggregationSourceNotFound):
        await _engine.run(
            dm.main_db,
            profile_id=profile["id"],
            source_diagram_id="00000000-0000-0000-0000-000000000000",
        )


# ─────────────────────────────────────────────────────────────────────
# Provenance comments (ADR-217)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_include_provenance_off_omits_comments(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """Default behaviour: no `<!-- iris:element=...` substring anywhere."""
    c, dm, h = env
    set_id = await _create_set(c, h)
    aisle_meat = await _create_package(c, h, set_id, "Meat & Poultry")
    aisle_produce = await _create_package(c, h, set_id, "Produce")
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince",
        package_id=aisle_meat, data=_ATTR_BLUEPRINT,
    )
    carrot_id = await _create_element(
        c, h, set_id=set_id, name="Carrot",
        package_id=aisle_produce, data=_ATTR_BLUEPRINT,
    )
    source = (
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}}\n"
        f"- {{{{element:{carrot_id}:attr:attributes/Quantity/type=3}}}}"
    )
    diag_id = await _create_smart_md(c, h, set_id, source)
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Default no provenance", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.package_name",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}",
            },
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=diag_id,
    )
    assert "<!-- iris:element=" not in result.markdown


@pytest.mark.asyncio
async def test_include_provenance_on_appends_comment_per_line(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    """With include_provenance=True, every rendered shopping-list line
    ends with a `<!-- iris:element=<uuid> -->` comment carrying the row's
    element_id. Headings and section dividers MUST NOT get the comment.
    Per-source breakdown text (when enabled) appears UNAFFECTED, before
    the trailing comment."""
    c, dm, h = env
    set_id = await _create_set(c, h)
    aisle_meat = await _create_package(c, h, set_id, "Meat & Poultry")
    aisle_produce = await _create_package(c, h, set_id, "Produce")
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince",
        package_id=aisle_meat, data=_ATTR_BLUEPRINT,
    )
    carrot_id = await _create_element(
        c, h, set_id=set_id, name="Carrot",
        package_id=aisle_produce, data=_ATTR_BLUEPRINT,
    )
    # Two recipes so per-source breakdown has substance.
    rec_a = await _create_smart_md(
        c, h, set_id,
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=500}}}}\n"
        f"- {{{{element:{carrot_id}:attr:attributes/Quantity/type=2}}}}",
        name="Recipe A",
    )
    rec_b = await _create_smart_md(
        c, h, set_id,
        f"- {{{{element:{carrot_id}:attr:attributes/Quantity/type=1}}}}",
        name="Recipe B",
    )
    plan_id = await _create_smart_md(
        c, h, set_id,
        f"- {{{{diagram:{rec_a}}}}}\n- {{{{diagram:{rec_b}}}}}",
        name="Plan",
    )
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Provenance on", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                },
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.package_name",
                "aggregation_fn": "sum",
                "line_format": "- {element.name}: {sum_value}",
                "show_per_source_breakdown": True,
                "breakdown_format": " ({sources_joined})",
                "include_provenance": True,
            },
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=plan_id,
    )
    md = result.markdown
    # Heading lines must NOT carry the comment.
    for line in md.splitlines():
        if line.startswith("## "):
            assert "<!-- iris:element=" not in line, (
                f"Heading carried provenance comment: {line!r}"
            )
        if line.strip() == "":
            assert "<!-- iris:element=" not in line
    # Every list line (starts with "- ") ends with the comment, and the
    # element_id matches the correct row.
    list_lines = [ln for ln in md.splitlines() if ln.startswith("- ")]
    assert list_lines, "no shopping-list lines rendered"
    for line in list_lines:
        assert line.endswith(" -->"), f"missing trailing comment: {line!r}"
        assert "<!-- iris:element=" in line
    # Verify the right element_id is on each row by matching name.
    pork_lines = [ln for ln in list_lines if "Pork mince" in ln]
    carrot_lines = [ln for ln in list_lines if "Carrot" in ln]
    assert pork_lines and carrot_lines
    for ln in pork_lines:
        assert f"<!-- iris:element={pork_id} -->" in ln, ln
    for ln in carrot_lines:
        assert f"<!-- iris:element={carrot_id} -->" in ln, ln
    # Per-source breakdown text MUST appear before the comment, not
    # after it (comment is the very last thing on the line).
    for ln in list_lines:
        comment_start = ln.index("<!-- iris:element=")
        breakdown_idx = ln.find("(Recipe ")
        if breakdown_idx != -1:
            assert breakdown_idx < comment_start, (
                f"breakdown text appeared after the comment: {ln!r}"
            )


@pytest.mark.asyncio
async def test_blank_value_skipped(
    env: tuple[httpx.AsyncClient, DatabaseManager, dict],
) -> None:
    c, dm, h = env
    set_id = await _create_set(c, h)
    pork_id = await _create_element(
        c, h, set_id=set_id, name="Pork mince", data=_ATTR_BLUEPRINT,
    )
    # Fillable slot (=) — empty, should be skipped.
    diag_id = await _create_smart_md(
        c, h, set_id,
        f"- {{{{element:{pork_id}:attr:attributes/Quantity/type=}}}}",
    )
    profile = await create_aggregation_profile(
        dm.main_db,
        name="Skip blanks", description=None,
        set_id=None, is_global=True,
        profile_data={
            "traversal": {
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Quantity/type",
                    "skip_blank_values": True,
                },
            },
            "output": {"line_format": "- {element.name}"},
        },
        is_default_for_set=False, created_by=None,
    )
    result = await _engine.run(
        dm.main_db, profile_id=profile["id"], source_diagram_id=diag_id,
    )
    assert result.row_count == 0
