"""Issue #145: export service must work with positional (tuple) rows.

The SQLite adapter returns rows that support both ``row["col"]`` and
``row[0]`` thanks to ``aiosqlite.Row`` factory. The Supabase adapter
normalizes asyncpg records into plain tuples (see
``app/db/adapter.py::_normalize_row``) — tuples only support integer
indexing. ``app/export/service.py`` was reading every column via the
string form, so the production (Supabase) deployment hit a
``TypeError`` and surfaced an HTTP 500 from
``POST /api/export/diagram/{diagram_id}``.

These tests pin the row-conversion helpers to positional indexing so
both adapters work uniformly.
"""

from __future__ import annotations

from app.export.service import _row_to_diagram, _row_to_element, _row_to_package


def test_row_to_diagram_accepts_tuple_row() -> None:
    row = (
        "diag-id",          # id
        "doview_analysis",  # diagram_type
        1,                  # current_version
        "Diagram name",     # name
        "desc",             # description
        '{"content": "hi"}',# data
        "2026-05-16T00:00:00+00:00",
        "user-id",
        "2026-05-16T00:00:00+00:00",
        "pkg-id",
        "set-id",
        "markdown",         # notation
    )

    diagram = _row_to_diagram(row)

    assert diagram.id == "diag-id"
    assert diagram.notation == "markdown"
    assert diagram.data == {"content": "hi"}
    assert diagram.parent_package_id == "pkg-id"
    assert diagram.set_id == "set-id"


def test_row_to_element_accepts_tuple_row() -> None:
    row = (
        "elem-id",
        "Component",
        1,
        "Widget",
        "desc",
        "{}",
        "2026-05-16T00:00:00+00:00",
        "user-id",
        "2026-05-16T00:00:00+00:00",
        "set-id",
        "simple",
    )

    element = _row_to_element(row)

    assert element.id == "elem-id"
    assert element.element_type == "Component"
    assert element.set_id == "set-id"


def test_row_to_package_accepts_tuple_row() -> None:
    row = (
        "pkg-id",
        1,
        "Root",
        "desc",
        "2026-05-16T00:00:00+00:00",
        "user-id",
        "2026-05-16T00:00:00+00:00",
        None,
        "set-id",
    )

    package = _row_to_package(row)

    assert package.id == "pkg-id"
    assert package.name == "Root"
    assert package.parent_package_id is None
    assert package.set_id == "set-id"
