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

# z-index so the zone fill renders behind its child capabilities (EA draws
# children on top of the zone), while notes float above everything.
_Z_ZONE = 0
_Z_CAPABILITY = 2
_Z_NOTE = 3


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
        node["zIndex"] = _Z_ZONE if arch == ZONE else _Z_CAPABILITY
    return True
