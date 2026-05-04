"""Deterministic Markdown templates for each export bundle (SPEC-128-A).

Templates output:
- one H1 with the entity name
- a metadata table
- a description block
- relationship / child tables where applicable

Output is deterministic: no timestamps, UUIDs, or locale-sensitive
formatting inside the body (the exported_at stamp is rendered once at
the top only). Snapshot tests cover every template.
"""

from __future__ import annotations

from app.export.schemas import (
    CollectionExport,
    DiagramExport,
    ElementExport,
    PackageExport,
    SetExport,
)


def render_diagram(bundle: DiagramExport) -> str:
    d = bundle.diagram
    lines: list[str] = [
        f"# {d.name}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Type | {d.diagram_type} |",
        f"| Notation | {d.notation} |",
        f"| Version | {d.current_version} |",
        f"| Set | {d.set_id or '_none_'} |",
        "",
        "## Description",
        "",
        d.description or "_No description._",
        "",
    ]
    if bundle.elements:
        lines.append(f"## Linked Elements ({len(bundle.elements)})")
        lines.append("")
        lines.append("| Name | Type | Notation |")
        lines.append("|---|---|---|")
        for e in sorted(bundle.elements, key=lambda x: x.name):
            lines.append(f"| {e.name} | {e.element_type} | {e.notation} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_element(bundle: ElementExport) -> str:
    e = bundle.element
    lines: list[str] = [
        f"# {e.name}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Type | {e.element_type} |",
        f"| Notation | {e.notation} |",
        f"| Version | {e.current_version} |",
        f"| Set | {e.set_id or '_none_'} |",
        "",
        "## Description",
        "",
        e.description or "_No description._",
        "",
    ]
    if bundle.linked_diagram_ids:
        lines.append(f"## Referenced In ({len(bundle.linked_diagram_ids)} diagrams)")
        lines.append("")
        for did in sorted(bundle.linked_diagram_ids):
            lines.append(f"- {did}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_package(bundle: PackageExport) -> str:
    p = bundle.package
    lines: list[str] = [
        f"# {p.name}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Version | {p.current_version} |",
        f"| Parent | {p.parent_package_id or '_root_'} |",
        f"| Set | {p.set_id or '_none_'} |",
        "",
        "## Description",
        "",
        p.description or "_No description._",
        "",
    ]
    if bundle.descendant_packages:
        lines.append(f"## Descendant Packages ({len(bundle.descendant_packages)})")
        lines.append("")
        for dp in sorted(bundle.descendant_packages, key=lambda x: x.name):
            lines.append(f"- **{dp.name}**")
        lines.append("")
    if bundle.diagrams:
        lines.append(f"## Diagrams ({len(bundle.diagrams)})")
        lines.append("")
        lines.append("| Name | Type | Notation |")
        lines.append("|---|---|---|")
        for d in sorted(bundle.diagrams, key=lambda x: x.name):
            lines.append(f"| {d.name} | {d.diagram_type} | {d.notation} |")
        lines.append("")
    if bundle.elements:
        lines.append(f"## Elements ({len(bundle.elements)})")
        lines.append("")
        lines.append("| Name | Type | Notation |")
        lines.append("|---|---|---|")
        for e in sorted(bundle.elements, key=lambda x: x.name):
            lines.append(f"| {e.name} | {e.element_type} | {e.notation} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_set(bundle: SetExport) -> str:
    s = bundle.set_
    lines: list[str] = [
        f"# {s.name}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Collection | {s.collection_id or '_standalone_'} |",
        "",
        "## Description",
        "",
        s.description or "_No description._",
        "",
        f"## Packages ({len(bundle.packages)})",
        "",
    ]
    if bundle.packages:
        for p in sorted(bundle.packages, key=lambda x: x.name):
            lines.append(f"- **{p.name}**")
        lines.append("")
    else:
        lines.append("_No packages._")
        lines.append("")

    lines.append(f"## Diagrams ({len(bundle.diagrams)})")
    lines.append("")
    if bundle.diagrams:
        lines.append("| Name | Type | Notation |")
        lines.append("|---|---|---|")
        for d in sorted(bundle.diagrams, key=lambda x: x.name):
            lines.append(f"| {d.name} | {d.diagram_type} | {d.notation} |")
        lines.append("")
    else:
        lines.append("_No diagrams._")
        lines.append("")

    lines.append(f"## Elements ({len(bundle.elements)})")
    lines.append("")
    if bundle.elements:
        lines.append("| Name | Type | Notation |")
        lines.append("|---|---|---|")
        for e in sorted(bundle.elements, key=lambda x: x.name):
            lines.append(f"| {e.name} | {e.element_type} | {e.notation} |")
        lines.append("")
    else:
        lines.append("_No elements._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_collection(bundle: CollectionExport) -> str:
    c = bundle.collection
    lines: list[str] = [
        f"# {c.name}",
        "",
        "## Description",
        "",
        c.description or "_No description._",
        "",
        f"## Sets ({len(bundle.sets)})",
        "",
    ]
    for s in bundle.sets:
        lines.append(f"### {s.set_.name}")
        lines.append("")
        lines.append(
            f"Packages: {len(s.packages)} · Diagrams: {len(s.diagrams)} · "
            f"Elements: {len(s.elements)}",
        )
        lines.append("")
        if s.set_.description:
            lines.append(s.set_.description)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
