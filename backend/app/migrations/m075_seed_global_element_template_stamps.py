"""Migration 075: seed five global element-template stamps (ADR-211).

Ships the canonical "Quantified item / Sized story / Logged work / Line
item / Read entry" stamps as ``is_global = 1`` element_templates with
deterministic UUIDv5 IDs so re-running is a no-op.

Each template carries a markdown_stamp using `{{self:…}}` placeholders
plus a ``template_data`` blueprint that pre-fills attribute slots so
elements created from the template are immediately compatible with the
matching aggregation profile (added in m076 / ADR-212).

Idempotent via INSERT OR IGNORE.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m075_seed_global_element_template_stamps"

# Stable namespace for UUIDv5 — anything constant works; this is the
# uuid.NAMESPACE_DNS variant with a fixed string so future re-runs and
# Supabase mirror produce identical IDs.
_STAMP_NAMESPACE = uuid.UUID("c1f5b6e0-1b4e-4f1c-9a2d-211211211211")

_SYSTEM_USER_ID = None  # element_templates.created_by is nullable; users aren't seeded at migration time


def _blueprint(element_type: str, attribute_names: list[str]) -> dict:
    """Build a template_data blueprint that pre-fills attribute slots."""
    return {
        "element_type": element_type,
        "notation": "simple",
        "data": {
            "attributes": [
                {
                    "name": attr_name,
                    "type": "",
                    "scope": "Public",
                    "notes": "",
                    "lower_bound": "",
                    "upper_bound": "",
                }
                for attr_name in attribute_names
            ],
        },
    }


SEEDED_STAMPS = [
    {
        "name": "Quantified item",
        "description": (
            "Element with a numeric quantity + unit (groceries, parts, "
            "stock items, line items in a list with totals). Pairs with "
            "the 'Shopping list' / sum-by-unit aggregation profile."
        ),
        "element_type": "class",
        "attributes": ["Quantity", "Unit"],
        "markdown_stamp": (
            "{{self:attr:attributes/Quantity/type=}} "
            "{{self:attr:attributes/Unit/type}} "
            "{{self:name}}"
        ),
    },
    {
        "name": "Sized story",
        "description": (
            "Work item with story points. Pairs with the 'Sprint points "
            "rollup' aggregation profile."
        ),
        "element_type": "class",
        "attributes": ["Points"],
        "markdown_stamp": (
            "{{self:attr:attributes/Points/type=}} pts — {{self:name}}"
        ),
    },
    {
        "name": "Logged work",
        "description": (
            "Work-log entry with hours. Pairs with the 'Time tracker "
            "rollup' aggregation profile."
        ),
        "element_type": "class",
        "attributes": ["Hours"],
        "markdown_stamp": (
            "{{self:attr:attributes/Hours/type=}}h — {{self:name}}"
        ),
    },
    {
        "name": "Line item",
        "description": (
            "Expense / billing line item. Pairs with the 'Expense report' "
            "aggregation profile."
        ),
        "element_type": "class",
        "attributes": ["Amount", "Currency"],
        "markdown_stamp": (
            "{{self:attr:attributes/Currency/type}}"
            "{{self:attr:attributes/Amount/type=}} — {{self:name}}"
        ),
    },
    {
        "name": "Read entry",
        "description": (
            "Reading-log entry. Pairs with the 'Reading log rollup' "
            "aggregation profile."
        ),
        "element_type": "class",
        "attributes": ["Pages", "Author"],
        "markdown_stamp": (
            "{{self:attr:attributes/Pages/type=}} pages — "
            "\"{{self:name}}\" by {{self:attr:attributes/Author/type}}"
        ),
    },
]


def stamp_id_for(name: str) -> str:
    """Deterministic UUIDv5 for a stamp name. Stable across re-runs and
    across SQLite/Supabase so the two seeds produce identical rows."""
    return str(uuid.uuid5(_STAMP_NAMESPACE, f"global-stamp:{name}"))


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — INSERT OR IGNORE."""
    now = datetime.now(tz=UTC).isoformat()
    for stamp in SEEDED_STAMPS:
        template_data = _blueprint(stamp["element_type"], stamp["attributes"])
        await db.execute(
            "INSERT OR IGNORE INTO element_templates ("
            "id, name, description, set_id, is_global, "
            "source_element_id, included_fields, template_data, "
            "markdown_stamp, created_by, created_at, updated_at"
            ") VALUES (?, ?, ?, NULL, 1, NULL, ?, ?, ?, ?, ?, ?)",
            (
                stamp_id_for(stamp["name"]),
                stamp["name"],
                stamp["description"],
                json.dumps(["element_type", "notation", "data"]),
                json.dumps(template_data),
                stamp["markdown_stamp"],
                _SYSTEM_USER_ID,
                now,
                now,
            ),
        )
    await db.commit()
