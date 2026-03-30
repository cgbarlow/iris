"""Maps Iris entities to MNEMOS engrams (ADR-111).

Each Iris entity (element, relationship, diagram) maps to one MNEMOS engram
with structured content, neuro-tags for filtering, and a source URI for
provenance.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


def element_to_engram(
    element_id: str,
    element_type: str,
    name: str,
    description: str | None,
    data: dict[str, Any] | None,
    set_id: str | None,
) -> dict[str, Any]:
    """Convert an Iris element to a MNEMOS engram dict."""
    content = f"[{element_type}] {name}"
    if description:
        content += f": {description}"

    # Include notable data fields
    if data:
        extras = []
        for key in ("stereotype", "technology", "language", "database"):
            val = data.get(key)
            if val:
                extras.append(f"{key}={val}")
        if extras:
            content += f" ({', '.join(extras)})"

    tags = ["element", f"type:{element_type}"]
    if set_id:
        tags.append(f"set:{set_id}")

    return {
        "content": content,
        "source": f"iris://elements/{element_id}",
        "neuro_tags": tags,
        "confidence": 0.9,
        "metadata": {
            "iris_id": element_id,
            "iris_type": "element",
            "element_type": element_type,
            "set_id": set_id,
        },
    }


def relationship_to_engram(
    rel_id: str,
    relationship_type: str,
    source_name: str,
    target_name: str,
    label: str | None,
    set_id: str | None,
) -> dict[str, Any]:
    """Convert an Iris relationship to a MNEMOS engram dict."""
    content = f"{source_name} --[{relationship_type}]--> {target_name}"
    if label:
        content += f": {label}"

    tags = ["relationship", f"rel_type:{relationship_type}"]
    if set_id:
        tags.append(f"set:{set_id}")

    return {
        "content": content,
        "source": f"iris://relationships/{rel_id}",
        "neuro_tags": tags,
        "confidence": 0.85,
        "metadata": {
            "iris_id": rel_id,
            "iris_type": "relationship",
            "relationship_type": relationship_type,
            "set_id": set_id,
        },
    }


def diagram_to_engram(
    diagram_id: str,
    diagram_type: str,
    name: str,
    description: str | None,
    set_id: str | None,
    package_id: str | None,
) -> dict[str, Any]:
    """Convert an Iris diagram to a MNEMOS engram dict."""
    content = f"[{diagram_type}] {name}"
    if description:
        content += f": {description}"

    tags = ["diagram", f"diagram_type:{diagram_type}"]
    if set_id:
        tags.append(f"set:{set_id}")
    if package_id:
        tags.append(f"pkg:{package_id}")

    return {
        "content": content,
        "source": f"iris://diagrams/{diagram_id}",
        "neuro_tags": tags,
        "confidence": 0.85,
        "metadata": {
            "iris_id": diagram_id,
            "iris_type": "diagram",
            "diagram_type": diagram_type,
            "set_id": set_id,
            "package_id": package_id,
        },
    }


def docref_chunk_to_engram(
    chunk_id: str,
    chunk_ref: str,
    content: str,
    document_id: str,
    document_title: str,
) -> dict[str, Any]:
    """Convert a DocRef legislation chunk to a MNEMOS engram dict."""
    return {
        "content": f"[{chunk_ref}] {content}",
        "source": f"iris://docref/{document_id}/{chunk_ref}",
        "neuro_tags": ["docref", f"doc:{document_id}"],
        "confidence": 0.9,
        "metadata": {
            "iris_id": chunk_id,
            "iris_type": "docref_chunk",
            "document_id": document_id,
            "document_title": document_title,
            "chunk_ref": chunk_ref,
        },
    }


async def build_all_engrams(db: DatabasePort) -> list[dict[str, Any]]:
    """Build engrams for all active entities in the database.

    Used for bulk reindex operations. Includes Iris elements, relationships,
    diagrams, and DocRef legislation chunks.
    """
    engrams: list[dict[str, Any]] = []

    # Elements
    cursor = await db.execute(
        """
        SELECT e.id, e.element_type, ev.name, ev.description, ev.data, e.set_id
        FROM elements e
        JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version
        WHERE e.is_deleted = 0
        ORDER BY ev.name ASC
        """,
    )
    for eid, etype, ename, edesc, edata_raw, eset_id in await cursor.fetchall():
        edata = json.loads(str(edata_raw)) if edata_raw else {}
        engrams.append(element_to_engram(eid, etype, ename, edesc, edata, eset_id))

    # Relationships (with element names for content)
    cursor = await db.execute(
        """
        SELECT r.id, r.relationship_type,
               evsrc.name, evtgt.name,
               rv.label, esrc.set_id
        FROM relationships r
        JOIN elements esrc ON r.source_element_id = esrc.id
        JOIN element_versions evsrc ON esrc.id = evsrc.element_id
            AND esrc.current_version = evsrc.version
        JOIN elements etgt ON r.target_element_id = etgt.id
        JOIN element_versions evtgt ON etgt.id = evtgt.element_id
            AND etgt.current_version = evtgt.version
        LEFT JOIN (
            SELECT relationship_id, label
            FROM relationship_versions rv2
            WHERE rv2.version = (
                SELECT MAX(rv3.version)
                FROM relationship_versions rv3
                WHERE rv3.relationship_id = rv2.relationship_id
            )
        ) rv ON rv.relationship_id = r.id
        WHERE r.is_deleted = 0
        """,
    )
    for rid, rtype, src_name, tgt_name, label, set_id in await cursor.fetchall():
        engrams.append(relationship_to_engram(rid, rtype, src_name, tgt_name, label, set_id))

    # Diagrams
    cursor = await db.execute(
        """
        SELECT d.id, d.diagram_type, dv.name, dv.description, d.set_id, d.parent_package_id
        FROM diagrams d
        JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version
        WHERE d.is_deleted = 0
        ORDER BY dv.name ASC
        """,
    )
    for did, dtype, dname, ddesc, dset_id, dpkg_id in await cursor.fetchall():
        engrams.append(diagram_to_engram(did, dtype, dname, ddesc, dset_id, dpkg_id))

    # DocRef legislation chunks — indexed with iris_type="docref_chunk".
    # Architecture queries filter to iris_type in [element, relationship, diagram],
    # so docref chunks never pollute set search results (ADR-113).
    try:
        cursor = await db.execute(
            """
            SELECT c.id, c.chunk_id, c.content, c.document_id, d.title
            FROM docref_chunks c
            JOIN docref_documents d ON c.document_id = d.id
            WHERE d.status = 'imported'
            ORDER BY d.title ASC, c.sort_order ASC
            """,
        )
        for cid, chunk_ref, content, doc_id, doc_title in await cursor.fetchall():
            engrams.append(docref_chunk_to_engram(cid, chunk_ref, content, doc_id, doc_title))
    except Exception:  # noqa: BLE001
        pass  # docref tables may not exist if extension never installed

    return engrams
