"""Migration 077: seed five global aggregation profiles (ADR-212).

Ships the canonical "Shopping list / Sprint points rollup / Time
tracker rollup / Expense report / Reading log rollup" profiles paired
1-for-1 with the element-template stamps seeded in m075 (ADR-211).

Each profile is a generic ruleset that drives the aggregation engine
(``backend/app/aggregation/``). The engine knows nothing about the
domain; the profile encodes which attribute carries the value to sum,
which (if any) groups items into buckets, and how to format output.

Idempotent via INSERT OR IGNORE with deterministic UUIDv5 ids.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m077_seed_global_aggregation_profiles"

_PROFILE_NAMESPACE = uuid.UUID("c1f5b6e0-1b4e-4f1c-9a2d-212212212212")


def profile_id_for(name: str) -> str:
    """Stable UUIDv5 across SQLite and Supabase. Matches m082."""
    return str(uuid.uuid5(_PROFILE_NAMESPACE, f"global-profile:{name}"))


# Shared output bits.
_LINE_FORMAT = (
    "- [{element.name}](iris://element/{element.id}) "
    "— {sum_value}{bucket_spaced}"
)
_BREAKDOWN_FORMAT = " ({sources_joined})"


SEEDED_PROFILES: list[dict] = [
    {
        "name": "Shopping list",
        "description": (
            "Sum ingredient quantities across the recipes referenced by "
            "a meal-plan diagram. Scales by per-meal diner count divided "
            "by the recipe's `data.servings`. Groups output by aisle "
            "(the ingredient's package_name). Pairs with the 'Quantified "
            "item' element template (ADR-211)."
        ),
        "profile_data": {
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                    "multiplier": {
                        "from_attribute_override":
                            "attributes/Diners/type",
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
                "group_by": "element.package_name",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "aggregation_fn": "sum",
                "line_format": _LINE_FORMAT,
                "show_per_source_breakdown": True,
                "breakdown_format": _BREAKDOWN_FORMAT,
            },
        },
    },
    {
        "name": "Sprint points rollup",
        "description": (
            "Sum story-points across the stories referenced by a sprint "
            "backlog diagram. Groups by element.package_name (commonly "
            "the team). Pairs with the 'Sized story' template (ADR-211)."
        ),
        "profile_data": {
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                },
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Points/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.package_name",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "aggregation_fn": "sum",
                "line_format": _LINE_FORMAT,
                "show_per_source_breakdown": False,
                "breakdown_format": _BREAKDOWN_FORMAT,
            },
        },
    },
    {
        "name": "Time tracker rollup",
        "description": (
            "Sum logged hours across the daily-log diagrams referenced "
            "by a period-of-time diagram. Groups by element.package_name "
            "(commonly the client or project). Pairs with the 'Logged "
            "work' template (ADR-211)."
        ),
        "profile_data": {
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                },
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Hours/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.package_name",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "aggregation_fn": "sum",
                "line_format": _LINE_FORMAT,
                "show_per_source_breakdown": False,
                "breakdown_format": _BREAKDOWN_FORMAT,
            },
        },
    },
    {
        "name": "Expense report",
        "description": (
            "Sum expense amounts across the receipt diagrams referenced "
            "by a reporting-period diagram. Bucketed by currency, "
            "grouped by element.package_name (commonly the category). "
            "Pairs with the 'Line item' template (ADR-211)."
        ),
        "profile_data": {
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                },
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Amount/type",
                    "bucket_attribute_path": "attributes/Currency/type",
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.package_name",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "aggregation_fn": "sum",
                "line_format": _LINE_FORMAT,
                "show_per_source_breakdown": False,
                "breakdown_format": _BREAKDOWN_FORMAT,
            },
        },
    },
    {
        "name": "Reading log rollup",
        "description": (
            "Sum pages read across the reading-log diagrams in a "
            "reading period. Groups by author (a structured element "
            "attribute). Pairs with the 'Read entry' template (ADR-211)."
        ),
        "profile_data": {
            "traversal": {
                "outer": {
                    "collect_token_type": "diagram",
                },
                "inner": {
                    "collect_token_type": "element",
                    "value_attribute_path": "attributes/Pages/type",
                    "bucket_attribute_path": None,
                    "skip_blank_values": True,
                },
            },
            "output": {
                "group_by": "element.attributes.Author/type",
                "sort_groups": "alpha",
                "sort_items_within_group": "alpha",
                "aggregation_fn": "sum",
                "line_format": _LINE_FORMAT,
                "show_per_source_breakdown": False,
                "breakdown_format": _BREAKDOWN_FORMAT,
            },
        },
    },
]


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    now = datetime.now(tz=UTC).isoformat()
    for profile in SEEDED_PROFILES:
        await db.execute(
            "INSERT OR IGNORE INTO aggregation_profiles ("
            "id, name, description, set_id, is_global, profile_data, "
            "is_default_for_set, created_by, created_at, updated_at"
            ") VALUES (?, ?, ?, NULL, 1, ?, 0, NULL, ?, ?)",
            (
                profile_id_for(profile["name"]),
                profile["name"],
                profile["description"],
                json.dumps(profile["profile_data"]),
                now,
                now,
            ),
        )
    await db.commit()
