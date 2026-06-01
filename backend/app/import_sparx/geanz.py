"""GEANZ Common Business Capabilities archetype classification + visual
enrichment (ADR-230).

Every GEANZ element imports as Iris ``element_type='capability'`` with
stereotype ``ArchiMate_Capability``; the three visual classes (zone,
capability, theme pill) and the proposed/redirect variant are
distinguishable only by the element NAME suffix and the cross-package
``qualifier='CBC Themes'`` signal. The EA fill/border/size already lands
on each canvas node's ``data.visual``; this module adds the presentation
deltas the EA raster shows but the importer did not capture — rounded
corners, dashed borders for theme pills + redirects, pill shape + italic
for theme pills — and lowers the zone's z-index so it sits behind its
child capabilities.

Shared by the Sparx importer (``import_sparx/service.py``) and the
data-repair script (``scripts/repair_geanz_render.py``) so the rule has a
single home (Protocol §13 DRY).
"""

from __future__ import annotations

ZONE = "geanz_zone"
CAPABILITY = "geanz_capability"
PROPOSED = "geanz_proposed_capability"
THEME_PILL = "geanz_theme_pill"

# Notes float above everything; capability z-index is computed per containment
# depth in apply_geanz_styling (a containing box sits behind the boxes it holds).
_Z_NOTE = 1000


def classify_geanz_archetype(label: str | None, qualifier: str | None = None) -> str:
    """Classify a capability node into a GEANZ archetype from its name + qualifier."""
    name = (label or "").strip().lower()
    if qualifier == "CBC Themes" or name.endswith("(theme)"):
        return THEME_PILL
    if name.endswith("(redirect)") or name.endswith("(proposed)"):
        return PROPOSED
    if name.endswith("capability zone"):
        return ZONE
    return CAPABILITY


def enrich_visual(archetype: str, visual: dict[str, object] | None) -> dict[str, object]:
    """Return ``visual`` with GEANZ presentation deltas added.

    Non-destructive for authentic EA values (fill / border colour / width /
    explicit size are preserved); only adds corner radius, dashed border,
    pill shape and italic where the archetype calls for it.
    """
    v: dict[str, object] = dict(visual or {})
    if archetype == ZONE:
        v.setdefault("borderRadius", 14)
    elif archetype == THEME_PILL:
        v["borderStyle"] = "dashed"
        v["cornerStyle"] = "pill"
        v["italic"] = True
    elif archetype == PROPOSED:
        v["borderStyle"] = "dashed"
        v.setdefault("borderRadius", 10)
    else:  # CAPABILITY
        v.setdefault("borderRadius", 10)
    return v


def _node_rect(node: dict[str, object]) -> tuple[float, float, float, float] | None:
    """(left, top, right, bottom) from the node's position + visual/measured
    size, or None if unknown."""
    pos = node.get("position")
    if not isinstance(pos, dict):
        return None
    x, y = pos.get("x"), pos.get("y")
    data = node.get("data")
    visual = data.get("visual") if isinstance(data, dict) else None
    w = h = None
    if isinstance(visual, dict):
        w, h = visual.get("width"), visual.get("height")
    measured = node.get("measured")
    if (w is None or h is None) and isinstance(measured, dict):
        w = w if w is not None else measured.get("width")
        h = h if h is not None else measured.get("height")
    if not all(isinstance(v, (int, float)) for v in (x, y, w, h)):
        return None
    return (x, y, x + w, y + h)  # type: ignore[operator]


def _rect_contains(outer: tuple, inner: tuple, tol: float = 1.0) -> bool:
    """True when ``outer`` encloses ``inner`` and is strictly larger in area
    (so two equal rects don't each 'contain' the other)."""
    if not (outer[0] <= inner[0] + tol and outer[1] <= inner[1] + tol
            and outer[2] >= inner[2] - tol and outer[3] >= inner[3] - tol):
        return False
    return (outer[2] - outer[0]) * (outer[3] - outer[1]) > (inner[2] - inner[0]) * (inner[3] - inner[1])


def _entity_type(node: dict[str, object]) -> str:
    data = node.get("data")
    if isinstance(data, dict):
        et = data.get("entityType")
        if isinstance(et, str):
            return et
    t = node.get("type")
    return t if isinstance(t, str) else ""


def is_geanz_diagram(nodes: list[dict[str, object]]) -> bool:
    """True when any capability node carries a GEANZ archetype marker
    (a zone / theme-pill / redirect name). A generic ArchiMate diagram with
    a capability named e.g. 'Payroll' does NOT match, so non-GEANZ imports
    are left untouched.
    """
    for node in nodes:
        if _entity_type(node) != "capability":
            continue
        data = node.get("data")
        if not isinstance(data, dict):
            continue
        arch = classify_geanz_archetype(
            data.get("label") if isinstance(data.get("label"), str) else None,
            data.get("qualifier") if isinstance(data.get("qualifier"), str) else None,
        )
        if arch in (ZONE, THEME_PILL, PROPOSED):
            return True
    return False


def apply_geanz_styling(nodes: list[dict[str, object]]) -> bool:
    """If ``nodes`` look like a GEANZ capability diagram, enrich each
    capability node's ``data.visual`` and set its z-index in place.

    Returns True when GEANZ styling was applied (so callers can set the
    diagram's ``theme_id='geanz-default'``), False otherwise. Idempotent —
    re-running yields the same result.
    """
    if not is_geanz_diagram(nodes):
        return False
    capability_nodes = []
    for node in nodes:
        et = _entity_type(node)
        if et == "note":
            node["zIndex"] = _Z_NOTE
            continue
        if et != "capability":
            continue
        data = node.get("data")
        if not isinstance(data, dict):
            continue
        arch = classify_geanz_archetype(
            data.get("label") if isinstance(data.get("label"), str) else None,
            data.get("qualifier") if isinstance(data.get("qualifier"), str) else None,
        )
        visual = data.get("visual")
        data["visual"] = enrich_visual(arch, visual if isinstance(visual, dict) else None)
        capability_nodes.append(node)

    # Layer by containment so a box that geometrically CONTAINS others renders
    # BEHIND them (else a mid-level container like "Payroll" covers its nested
    # sub-capabilities). z-index = how many other boxes contain this one, so a
    # zone (depth 0) sits behind its capabilities (depth 1) behind sub-caps
    # (depth 2). Notes float above everything (_Z_NOTE).
    rects = [(_node_rect(n), n) for n in capability_nodes]
    for rn, node in rects:
        depth = 0
        if rn is not None:
            for rm, other in rects:
                if other is not node and rm is not None and _rect_contains(rm, rn):
                    depth += 1
        node["zIndex"] = depth
    return True
