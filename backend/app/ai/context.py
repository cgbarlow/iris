"""Set context builder for AI Q&A (ADR-093, ADR-102).

Queries elements, relationships, and diagrams for a Set and formats them as
structured text for the LLM system prompt. Truncates proportionally if over budget.
Supports multi-set context for Collections (ADR-102).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort

# Rough heuristic: 4 chars ≈ 1 token
_CHARS_PER_TOKEN = 4


def _truncate_to_budget(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


async def build_set_context(
    db: DatabasePort,
    set_id: str,
    *,
    max_tokens: int = 8000,
    package_ids: list[str] | None = None,
) -> str:
    """Build a structured text context string for the given Set.

    Returns a string suitable for use as an LLM system prompt context.
    """
    max_chars = max_tokens * _CHARS_PER_TOKEN

    # 1. Set metadata
    cursor = await db.execute(
        "SELECT name, description FROM sets WHERE id = ?",
        (set_id,),
    )
    set_row = await cursor.fetchone()
    if set_row is None:
        return f"Set {set_id} not found."
    set_name, set_desc = set_row

    header = f"SET: {set_name}\n"
    if set_desc:
        header += f"{set_desc}\n"
    header += "\n"

    # 2. Elements in set — elements.set_id column (no join table)
    cursor = await db.execute(
        """
        SELECT e.id, e.element_type, ev.name, ev.description, ev.data
        FROM elements e
        JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version
        WHERE e.set_id = ? AND e.is_deleted = 0
        ORDER BY ev.name ASC
        """,
        (set_id,),
    )
    element_rows = await cursor.fetchall()

    elements_lines: list[str] = []
    element_ids: set[str] = set()
    for eid, etype, ename, edesc, edata_raw in element_rows:
        element_ids.add(eid)
        line = f"- [{etype}] {ename}"
        if edesc:
            line += f": {edesc}"
        # Include notable data fields (stereotype, technology, etc.)
        try:
            edata = json.loads(edata_raw) if edata_raw else {}
            extras = []
            for key in ("stereotype", "technology", "language", "database"):
                val = edata.get(key)
                if val:
                    extras.append(f"{key}={val}")
            if extras:
                line += f" ({', '.join(extras)})"
        except (ValueError, TypeError):
            pass
        elements_lines.append(line)

    elements_section = f"ELEMENTS ({len(elements_lines)}):\n"
    if elements_lines:
        elements_section += "\n".join(elements_lines) + "\n"
    else:
        elements_section += "(none)\n"
    elements_section += "\n"

    # 3. Relationships between set elements
    rels_lines: list[str] = []
    if element_ids:
        placeholders = ",".join("?" * len(element_ids))
        cursor = await db.execute(
            f"""
            SELECT r.relationship_type, evsrc.name, evtgt.name
            FROM relationships r
            JOIN elements esrc ON r.source_element_id = esrc.id
            JOIN element_versions evsrc ON esrc.id = evsrc.element_id
                AND esrc.current_version = evsrc.version
            JOIN elements etgt ON r.target_element_id = etgt.id
            JOIN element_versions evtgt ON etgt.id = evtgt.element_id
                AND etgt.current_version = evtgt.version
            WHERE r.source_element_id IN ({placeholders})
              AND r.target_element_id IN ({placeholders})
              AND r.is_deleted = 0
            ORDER BY evsrc.name ASC, r.relationship_type ASC
            """,
            (*element_ids, *element_ids),
        )
        for rtype, src_name, tgt_name in await cursor.fetchall():
            rels_lines.append(f"- {src_name} --[{rtype}]--> {tgt_name}")

    rels_section = f"RELATIONSHIPS ({len(rels_lines)}):\n"
    if rels_lines:
        rels_section += "\n".join(rels_lines) + "\n"
    else:
        rels_section += "(none)\n"
    rels_section += "\n"

    # 4. Diagrams in set (optionally filtered by package)
    if package_ids:
        pkg_placeholders = ",".join("?" * len(package_ids))
        cursor = await db.execute(
            f"""
            SELECT m.diagram_type, mv.name, mv.description
            FROM diagrams m
            JOIN diagram_versions mv ON m.id = mv.diagram_id AND m.current_version = mv.version
            WHERE m.set_id = ? AND m.is_deleted = 0
              AND m.parent_package_id IN ({pkg_placeholders})
            ORDER BY mv.name ASC
            """,  # noqa: S608
            (set_id, *package_ids),
        )
    else:
        cursor = await db.execute(
            """
            SELECT m.diagram_type, mv.name, mv.description
            FROM diagrams m
            JOIN diagram_versions mv ON m.id = mv.diagram_id AND m.current_version = mv.version
            WHERE m.set_id = ? AND m.is_deleted = 0
            ORDER BY mv.name ASC
            """,
            (set_id,),
        )
    diag_rows = await cursor.fetchall()
    diag_lines = []
    for dtype, dname, ddesc in diag_rows:
        line = f"- [{dtype}] {dname}"
        if ddesc:
            line += f": {ddesc}"
        diag_lines.append(line)

    diags_section = f"DIAGRAMS ({len(diag_lines)}):\n"
    if diag_lines:
        diags_section += "\n".join(diag_lines) + "\n"
    else:
        diags_section += "(none)\n"

    # Assemble and truncate proportionally if needed
    full_text = header + elements_section + rels_section + diags_section
    if len(full_text) <= max_chars:
        return full_text

    # Proportional truncation across the three content sections
    header_chars = len(header)
    available = max_chars - header_chars
    # Split 50% elements, 30% rels, 20% diagrams
    elements_budget = int(available * 0.5)
    rels_budget = int(available * 0.3)
    diags_budget = available - elements_budget - rels_budget

    return (
        header
        + _truncate_to_budget(elements_section, elements_budget)
        + "\n"
        + _truncate_to_budget(rels_section, rels_budget)
        + "\n"
        + _truncate_to_budget(diags_section, diags_budget)
    )


async def build_multi_set_context(
    db: DatabasePort,
    set_ids: list[str],
    *,
    max_tokens: int = 8000,
    package_ids: list[str] | None = None,
) -> str:
    """Build combined context from multiple Sets, dividing token budget proportionally.

    Each set gets an equal share of the token budget. Results are concatenated
    with clear dividers between sets. When package_ids is provided, only
    diagrams within those packages are included in the context.
    """
    if not set_ids:
        return "No sets selected."

    if len(set_ids) == 1:
        return await build_set_context(db, set_ids[0], max_tokens=max_tokens, package_ids=package_ids)

    # Reserve tokens for preamble and dividers
    preamble = f"MULTI-SET CONTEXT ({len(set_ids)} sets):\n\n"
    divider_chars = len("\n---\n\n") * len(set_ids)
    preamble_chars = len(preamble) + divider_chars
    available_tokens = max_tokens - (preamble_chars // _CHARS_PER_TOKEN)

    per_set_tokens = max(available_tokens // len(set_ids), 500)

    sections: list[str] = []
    for sid in set_ids:
        ctx = await build_set_context(db, sid, max_tokens=per_set_tokens, package_ids=package_ids)
        sections.append(ctx)

    return preamble + "\n---\n\n".join(sections)
