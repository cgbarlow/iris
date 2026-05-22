"""Unit tests for the recipe-rewrite regex (issue #211 PR 6).

The DB-touching scripts in `scripts/` are exercised in dry-run against
the live UAT as part of the v6.22.0 deploy verification; here we just
validate the pure-function rewrite logic.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "rewriter",
        REPO_ROOT / "scripts" / "migrate_recipes_to_quantity_tokens.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_UUID = "a8db6014-584b-46bd-bc33-cfddc040cca4"


def test_rewrites_legacy_pattern() -> None:
    mod = _load_module()
    src = (
        f"- 500 {{{{element:{_UUID}:attr:attributes/Unit/type}}}} "
        f"{{{{element:{_UUID}:name}}}}"
    )
    new, count = mod._rewrite(src)
    assert count == 1
    assert f"{{{{element:{_UUID}:attr:attributes/Quantity/type=500}}}}" in new


def test_idempotent() -> None:
    mod = _load_module()
    src = (
        f"- 500 {{{{element:{_UUID}:attr:attributes/Unit/type}}}} "
        f"{{{{element:{_UUID}:name}}}}"
    )
    once, count1 = mod._rewrite(src)
    twice, count2 = mod._rewrite(once)
    assert count1 == 1
    assert count2 == 0
    assert twice == once


def test_decimal_quantities() -> None:
    mod = _load_module()
    src = (
        f"- 1.5 {{{{element:{_UUID}:attr:attributes/Unit/type}}}} "
        f"{{{{element:{_UUID}:name}}}}"
    )
    new, count = mod._rewrite(src)
    assert count == 1
    assert "Quantity/type=1.5}}" in new


def test_leaves_plain_name_lines_alone() -> None:
    """Lines like `- {{element:UUID:name}}` (no quantity, no Unit
    token) are passing prose mentions and should be untouched."""
    mod = _load_module()
    src = f"- {{{{element:{_UUID}:name}}}}"
    new, count = mod._rewrite(src)
    assert count == 0
    assert new == src


def test_multi_line() -> None:
    mod = _load_module()
    src = (
        f"- 500 {{{{element:{_UUID}:attr:attributes/Unit/type}}}} "
        f"{{{{element:{_UUID}:name}}}}\n"
        f"- 2 {{{{element:{_UUID}:attr:attributes/Unit/type}}}} "
        f"{{{{element:{_UUID}:name}}}}"
    )
    _, count = mod._rewrite(src)
    assert count == 2
