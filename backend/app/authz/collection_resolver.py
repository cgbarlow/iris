"""Resolve a write target's owning collection id (ADR-237).

Every writable entity roots at a collection: a set carries ``collection_id``
directly; a package / diagram / element / element_template carries ``set_id``,
which resolves to the set's collection. Returns ``None`` when there is no owning
collection — an un-grouped set (``collection_id IS NULL``, e.g. the seeded
default set), a global element template (``set_id IS NULL``), or a missing row.
The enforcement helper treats ``None`` as "outside any assigned collection".

These are deliberately lightweight FK lookups rather than the full service
getters: they stay off the write-path's critical latency and intentionally
ignore ``is_deleted`` so authz resolves the true owning collection regardless
of a row's soft-delete state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def _scalar(db: DatabasePort, sql: str, value: str) -> str | None:
    cursor = await db.execute(sql, (value,))
    row = await cursor.fetchone()
    return row[0] if row else None


async def collection_of_set(db: DatabasePort, set_id: str | None) -> str | None:
    """The collection a set belongs to (or ``None`` if un-grouped/missing)."""
    if not set_id:
        return None
    return await _scalar(db, "SELECT collection_id FROM sets WHERE id = ?", set_id)


async def collection_of_package(db: DatabasePort, package_id: str | None) -> str | None:
    if not package_id:
        return None
    set_id = await _scalar(db, "SELECT set_id FROM packages WHERE id = ?", package_id)
    return await collection_of_set(db, set_id)


async def collection_of_diagram(db: DatabasePort, diagram_id: str | None) -> str | None:
    if not diagram_id:
        return None
    set_id = await _scalar(db, "SELECT set_id FROM diagrams WHERE id = ?", diagram_id)
    return await collection_of_set(db, set_id)


async def collection_of_element(db: DatabasePort, element_id: str | None) -> str | None:
    if not element_id:
        return None
    set_id = await _scalar(db, "SELECT set_id FROM elements WHERE id = ?", element_id)
    return await collection_of_set(db, set_id)


async def collection_of_template(db: DatabasePort, template_id: str | None) -> str | None:
    """The collection a template belongs to. Global templates resolve to
    ``None`` (their ``set_id`` is NULL) — scoped users can't write them."""
    if not template_id:
        return None
    set_id = await _scalar(
        db, "SELECT set_id FROM element_templates WHERE id = ?", template_id
    )
    return await collection_of_set(db, set_id)


async def collection_of_entity(
    db: DatabasePort, entity_type: str, entity_id: str
) -> str | None:
    """Resolve the owning collection for any of the entity types used by the
    entity-image attachment surface (ADR-209): a ``collection`` IS its own
    collection; the rest delegate to the per-type resolvers above."""
    if entity_type == "collection":
        return entity_id
    if entity_type == "set":
        return await collection_of_set(db, entity_id)
    if entity_type == "package":
        return await collection_of_package(db, entity_id)
    if entity_type == "diagram":
        return await collection_of_diagram(db, entity_id)
    if entity_type == "element":
        return await collection_of_element(db, entity_id)
    return None
