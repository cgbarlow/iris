"""Bundle builders for `/api/export/*` (SPEC-128-A).

Each builder fetches raw rows from the main DB and assembles a Pydantic
bundle using the existing response models. The 10,000-element cap is
enforced at the bundle level: exceeding it raises `ExportTooLargeError`
which the router maps to HTTP 413.

These builders deliberately query the DB directly rather than calling
into each entity's service layer - keeping the export path a single
fast read without going through permission-decoding or hydration
pipelines designed for interactive editing.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.collections.models import CollectionResponse
from app.diagrams.models import DiagramResponse
from app.elements.models import ElementResponse
from app.export.schemas import (
    CollectionExport,
    DiagramExport,
    ElementExport,
    PackageExport,
    SetExport,
)
from app.packages.models import PackageResponse
from app.sets.models import SetResponse

if TYPE_CHECKING:
    import aiosqlite

MAX_ELEMENTS_PER_BUNDLE = 10_000


class ExportTooLargeError(Exception):
    """Raised when a bundle would exceed `MAX_ELEMENTS_PER_BUNDLE`."""

    def __init__(self, count: int, limit: int) -> None:
        super().__init__(f"Export exceeds {limit} elements ({count})")
        self.count = count
        self.limit = limit


class ExportNotFoundError(Exception):
    """Raised when the requested entity does not exist or is soft-deleted."""


def _now() -> datetime:
    return datetime.now(tz=UTC)


# --- Diagram ------------------------------------------------------------------

_DIAGRAM_SELECT = (
    "SELECT d.id, d.diagram_type, d.current_version, dv.name, dv.description,"
    " dv.data, d.created_at, d.created_by, d.updated_at, d.parent_package_id,"
    " d.set_id, d.notation"
    " FROM diagrams d"
    " JOIN diagram_versions dv"
    "   ON d.id = dv.diagram_id AND d.current_version = dv.version"
)

_ELEMENT_SELECT = (
    "SELECT e.id, e.element_type, e.current_version, ev.name, ev.description,"
    " ev.data, e.created_at, e.created_by, e.updated_at, e.set_id, e.notation"
    " FROM elements e"
    " JOIN element_versions ev"
    "   ON e.id = ev.element_id AND e.current_version = ev.version"
)

_PACKAGE_SELECT = (
    "SELECT p.id, p.current_version, pv.name, pv.description, p.created_at,"
    " p.created_by, p.updated_at, p.parent_package_id, p.set_id"
    " FROM packages p"
    " JOIN package_versions pv"
    "   ON p.id = pv.package_id AND p.current_version = pv.version"
)


async def _fetch_diagram(db: aiosqlite.Connection, diagram_id: str) -> DiagramResponse:
    cursor = await db.execute(
        f"{_DIAGRAM_SELECT}"
        " WHERE d.id = ? AND (d.is_deleted = 0 OR d.is_deleted IS NULL)",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ExportNotFoundError(f"Diagram {diagram_id} not found")
    return _row_to_diagram(row)


async def _fetch_elements_for_diagram(
    db: aiosqlite.Connection, diagram_id: str,
) -> list[ElementResponse]:
    """Return every element referenced by a diagram's canvas nodes."""
    diagram = await _fetch_diagram(db, diagram_id)
    element_ids = _element_ids_from_diagram_data(diagram.data)
    if not element_ids:
        return []
    placeholders = ",".join("?" for _ in element_ids)
    cursor = await db.execute(
        f"{_ELEMENT_SELECT}"
        f" WHERE e.id IN ({placeholders})"
        " AND (e.is_deleted = 0 OR e.is_deleted IS NULL)",
        element_ids,
    )
    rows = await cursor.fetchall()
    return [_row_to_element(r) for r in rows]


async def build_diagram_export(
    db: aiosqlite.Connection, diagram_id: str,
) -> DiagramExport:
    diagram = await _fetch_diagram(db, diagram_id)
    elements = await _fetch_elements_for_diagram(db, diagram_id)
    return DiagramExport(exported_at=_now(), diagram=diagram, elements=elements)


# --- Element ------------------------------------------------------------------

async def _fetch_element(db: aiosqlite.Connection, element_id: str) -> ElementResponse:
    cursor = await db.execute(
        f"{_ELEMENT_SELECT}"
        " WHERE e.id = ? AND (e.is_deleted = 0 OR e.is_deleted IS NULL)",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ExportNotFoundError(f"Element {element_id} not found")
    return _row_to_element(row)


async def build_element_export(
    db: aiosqlite.Connection, element_id: str,
) -> ElementExport:
    element = await _fetch_element(db, element_id)

    # Which diagrams reference this element on their canvas?
    cursor = await db.execute(
        "SELECT d.id, dv.data FROM diagrams d"
        " JOIN diagram_versions dv"
        "   ON d.id = dv.diagram_id AND d.current_version = dv.version"
        " WHERE (d.is_deleted = 0 OR d.is_deleted IS NULL)",
    )
    linked: list[str] = [
        row["id"]
        for row in await cursor.fetchall()
        if element_id in _element_ids_from_diagram_data(_json_load(row["data"]))
    ]

    return ElementExport(
        exported_at=_now(), element=element, linked_diagram_ids=linked,
    )


# --- Package ------------------------------------------------------------------

async def _fetch_package(db: aiosqlite.Connection, package_id: str) -> PackageResponse:
    cursor = await db.execute(
        f"{_PACKAGE_SELECT}"
        " WHERE p.id = ? AND (p.is_deleted = 0 OR p.is_deleted IS NULL)",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ExportNotFoundError(f"Package {package_id} not found")
    return _row_to_package(row)


async def _descendant_package_ids(
    db: aiosqlite.Connection, root_id: str,
) -> list[str]:
    """Breadth-first descendants of a package (excludes the root itself)."""
    descendants: list[str] = []
    frontier = [root_id]
    seen = {root_id}
    while frontier:
        placeholders = ",".join("?" for _ in frontier)
        cursor = await db.execute(
            f"SELECT id FROM packages WHERE parent_package_id IN ({placeholders})"
            " AND (is_deleted = 0 OR is_deleted IS NULL)",
            frontier,
        )
        children = [r["id"] for r in await cursor.fetchall()]
        children = [c for c in children if c not in seen]
        descendants.extend(children)
        seen.update(children)
        frontier = children
    return descendants


async def build_package_export(
    db: aiosqlite.Connection, package_id: str,
) -> PackageExport:
    root = await _fetch_package(db, package_id)
    descendant_ids = await _descendant_package_ids(db, package_id)

    descendants: list[PackageResponse] = []
    if descendant_ids:
        placeholders = ",".join("?" for _ in descendant_ids)
        cursor = await db.execute(
            f"{_PACKAGE_SELECT}"
            f" WHERE p.id IN ({placeholders})"
            " AND (p.is_deleted = 0 OR p.is_deleted IS NULL)",
            descendant_ids,
        )
        descendants = [_row_to_package(r) for r in await cursor.fetchall()]

    all_package_ids = [package_id, *descendant_ids]
    placeholders = ",".join("?" for _ in all_package_ids)

    diag_cursor = await db.execute(
        f"{_DIAGRAM_SELECT}"
        f" WHERE d.parent_package_id IN ({placeholders})"
        " AND (d.is_deleted = 0 OR d.is_deleted IS NULL)",
        all_package_ids,
    )
    diagrams = [_row_to_diagram(r) for r in await diag_cursor.fetchall()]

    # Elements referenced by any of these diagrams.
    element_ids: set[str] = set()
    for d in diagrams:
        element_ids.update(_element_ids_from_diagram_data(d.data))
    elements: list[ElementResponse] = []
    if element_ids:
        placeholders = ",".join("?" for _ in element_ids)
        cursor = await db.execute(
            f"{_ELEMENT_SELECT}"
            f" WHERE e.id IN ({placeholders})"
            " AND (e.is_deleted = 0 OR e.is_deleted IS NULL)",
            list(element_ids),
        )
        elements = [_row_to_element(r) for r in await cursor.fetchall()]

    _enforce_cap(len(descendants) + len(diagrams) + len(elements))

    return PackageExport(
        exported_at=_now(),
        package=root,
        descendant_packages=descendants,
        diagrams=diagrams,
        elements=elements,
    )


# --- Set ----------------------------------------------------------------------

async def _fetch_set(db: aiosqlite.Connection, set_id: str) -> SetResponse:
    cursor = await db.execute(
        "SELECT id, name, description, created_at, created_by, updated_at,"
        " collection_id"
        " FROM sets"
        " WHERE id = ? AND (is_deleted = 0 OR is_deleted IS NULL)",
        (set_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ExportNotFoundError(f"Set {set_id} not found")
    return SetResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        created_by=row["created_by"] or "",
        updated_at=row["updated_at"],
        collection_id=row["collection_id"],
    )


async def build_set_export(db: aiosqlite.Connection, set_id: str) -> SetExport:
    set_ = await _fetch_set(db, set_id)

    pkg_cursor = await db.execute(
        f"{_PACKAGE_SELECT}"
        " WHERE p.set_id = ? AND (p.is_deleted = 0 OR p.is_deleted IS NULL)",
        (set_id,),
    )
    packages = [_row_to_package(r) for r in await pkg_cursor.fetchall()]

    diag_cursor = await db.execute(
        f"{_DIAGRAM_SELECT}"
        " WHERE d.set_id = ? AND (d.is_deleted = 0 OR d.is_deleted IS NULL)",
        (set_id,),
    )
    diagrams = [_row_to_diagram(r) for r in await diag_cursor.fetchall()]

    elem_cursor = await db.execute(
        f"{_ELEMENT_SELECT}"
        " WHERE e.set_id = ? AND (e.is_deleted = 0 OR e.is_deleted IS NULL)",
        (set_id,),
    )
    elements = [_row_to_element(r) for r in await elem_cursor.fetchall()]

    _enforce_cap(len(packages) + len(diagrams) + len(elements))

    return SetExport(
        exported_at=_now(),
        set=set_,
        packages=packages,
        diagrams=diagrams,
        elements=elements,
    )


# --- Collection ---------------------------------------------------------------

async def _fetch_collection(
    db: aiosqlite.Connection, collection_id: str,
) -> CollectionResponse:
    cursor = await db.execute(
        "SELECT id, name, description, created_at, created_by, updated_at"
        " FROM collections"
        " WHERE id = ? AND (is_deleted = 0 OR is_deleted IS NULL)",
        (collection_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ExportNotFoundError(f"Collection {collection_id} not found")
    return CollectionResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        created_by=row["created_by"] or "",
        updated_at=row["updated_at"],
    )


async def build_collection_export(
    db: aiosqlite.Connection, collection_id: str,
) -> CollectionExport:
    collection = await _fetch_collection(db, collection_id)
    cursor = await db.execute(
        "SELECT id FROM sets WHERE collection_id = ?"
        " AND (is_deleted = 0 OR is_deleted IS NULL)",
        (collection_id,),
    )
    set_ids = [r["id"] for r in await cursor.fetchall()]

    set_exports: list[SetExport] = []
    running_total = 0
    for sid in set_ids:
        sub = await build_set_export(db, sid)
        running_total += len(sub.packages) + len(sub.diagrams) + len(sub.elements)
        _enforce_cap(running_total)
        set_exports.append(sub)

    return CollectionExport(
        exported_at=_now(), collection=collection, sets=set_exports,
    )


# --- Helpers ------------------------------------------------------------------

def _json_load(raw: object) -> dict[str, object]:
    if raw is None:
        return {}
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode()
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _element_ids_from_diagram_data(data: dict[str, object]) -> list[str]:
    """Extract element IDs referenced on a canvas."""
    ids: list[str] = []
    nodes = data.get("nodes", [])
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_data = node.get("data", {})
            if isinstance(node_data, dict):
                eid = node_data.get("element_id") or node_data.get("entity_id")
                if isinstance(eid, str):
                    ids.append(eid)
    # Deduplicate preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _row_to_element(row: aiosqlite.Row) -> ElementResponse:
    return ElementResponse(
        id=row["id"],
        element_type=row["element_type"],
        current_version=row["current_version"],
        name=row["name"],
        description=row["description"],
        data=_json_load(row["data"]),
        created_at=row["created_at"],
        created_by=row["created_by"] or "",
        updated_at=row["updated_at"],
        set_id=row["set_id"],
        notation=row["notation"] or "simple",
    )


def _row_to_diagram(row: aiosqlite.Row) -> DiagramResponse:
    return DiagramResponse(
        id=row["id"],
        diagram_type=row["diagram_type"],
        current_version=row["current_version"],
        name=row["name"],
        description=row["description"],
        data=_json_load(row["data"]),
        created_at=row["created_at"],
        created_by=row["created_by"] or "",
        updated_at=row["updated_at"],
        parent_package_id=row["parent_package_id"],
        set_id=row["set_id"],
        notation=row["notation"] or "simple",
    )


def _row_to_package(row: aiosqlite.Row) -> PackageResponse:
    return PackageResponse(
        id=row["id"],
        current_version=row["current_version"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        created_by=row["created_by"] or "",
        updated_at=row["updated_at"],
        parent_package_id=row["parent_package_id"],
        set_id=row["set_id"],
    )


def _enforce_cap(count: int) -> None:
    # Read the module-level constant at call-time so tests can monkey-patch it.
    current = sys.modules[__name__].MAX_ELEMENTS_PER_BUNDLE
    if count > current:
        raise ExportTooLargeError(count, current)
