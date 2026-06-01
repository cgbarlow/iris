"""Tests for GEANZ archetype classification + visual enrichment (ADR-230 F5).

The same rule is used by the Sparx importer and the data-repair script,
so it is tested in isolation here.
"""

from __future__ import annotations

from app.import_sparx.geanz import (
    CAPABILITY,
    PROPOSED,
    THEME_PILL,
    ZONE,
    _Z_NOTE,
    apply_geanz_styling,
    classify_geanz_archetype,
    enrich_visual,
    is_geanz_diagram,
)


def test_classify_zone_by_name():
    assert classify_geanz_archetype("Customer Service Delivery capability zone") == ZONE


def test_classify_theme_pill_by_suffix_or_qualifier():
    assert classify_geanz_archetype("Strategy (theme)") == THEME_PILL
    assert classify_geanz_archetype("Operations", qualifier="CBC Themes") == THEME_PILL


def test_classify_redirect_as_proposed():
    assert classify_geanz_archetype("Product and Service Management (redirect)") == PROPOSED


def test_classify_plain_capability():
    assert classify_geanz_archetype("Case Management") == CAPABILITY


def test_enrich_zone_keeps_fill_adds_radius():
    v = enrich_visual(ZONE, {"bgColor": "#ccf2fe", "borderColor": "#4169e1", "borderWidth": 3})
    assert v["bgColor"] == "#ccf2fe"  # authentic EA fill preserved
    assert v["borderColor"] == "#4169e1"
    assert v["borderWidth"] == 3
    assert v["borderRadius"] == 14


def test_enrich_theme_pill_is_dashed_pill_italic():
    v = enrich_visual(THEME_PILL, {"bgColor": "#ffffff", "borderColor": "#4169e1"})
    assert v["borderStyle"] == "dashed"
    assert v["cornerStyle"] == "pill"
    assert v["italic"] is True


def test_enrich_proposed_is_dashed():
    v = enrich_visual(PROPOSED, {"bgColor": "#ffffff"})
    assert v["borderStyle"] == "dashed"
    assert v["borderRadius"] == 10


def test_enrich_capability_rounded():
    assert enrich_visual(CAPABILITY, {})["borderRadius"] == 10


def _node(label, *, qualifier=None, entity_type="capability", visual=None, position=None):
    data = {"label": label, "entityType": entity_type}
    if qualifier:
        data["qualifier"] = qualifier
    if visual is not None:
        data["visual"] = visual
    node = {"id": label, "type": entity_type, "data": data}
    if position is not None:
        node["position"] = position
    return node


def test_is_geanz_diagram_detects_zone():
    nodes = [_node("Customer Service Delivery capability zone"), _node("Case Management")]
    assert is_geanz_diagram(nodes) is True


def test_is_geanz_diagram_ignores_generic_archimate():
    # A plain ArchiMate capability diagram (no zone/theme/redirect names).
    nodes = [_node("Payroll"), _node("Procurement")]
    assert is_geanz_diagram(nodes) is False


def test_apply_geanz_styling_enriches_and_sets_zindex():
    # Containment: zone (0,0..900,500) ⊃ mid (10,10..810,410) ⊃ sub (20,20..120,90).
    zone = _node("Customer Service Delivery capability zone",
                 visual={"bgColor": "#ccf2fe", "borderColor": "#4169e1", "borderWidth": 3, "width": 900, "height": 500},
                 position={"x": 0, "y": 0})
    mid = _node("Payroll", visual={"bgColor": "#ffffff", "borderColor": "#4169e1", "borderWidth": 2, "width": 800, "height": 400},
                position={"x": 10, "y": 10})
    sub = _node("Case Management", visual={"bgColor": "#ffffff", "borderColor": "#4169e1", "width": 100, "height": 70},
                position={"x": 20, "y": 20})
    pill = _node("Strategy (theme)", qualifier="CBC Themes",
                 visual={"bgColor": "#ffffff", "borderColor": "#4169e1", "width": 120, "height": 30},
                 position={"x": 0, "y": -50})  # above the zone, contained by nothing
    note = _node("August 2025", entity_type="note", visual={"width": 148, "height": 30})
    nodes = [zone, mid, sub, pill, note]

    assert apply_geanz_styling(nodes) is True

    # Containment depth layering: zone behind mid behind sub.
    assert zone["zIndex"] == 0
    assert mid["zIndex"] == 1
    assert sub["zIndex"] == 2
    assert zone["zIndex"] < mid["zIndex"] < sub["zIndex"]
    assert pill["zIndex"] == 0  # not inside anything

    assert zone["data"]["visual"]["borderRadius"] == 14
    assert zone["data"]["visual"]["bgColor"] == "#ccf2fe"  # preserved
    assert sub["data"]["visual"]["borderRadius"] == 10
    assert pill["data"]["visual"]["borderStyle"] == "dashed"
    assert pill["data"]["visual"]["cornerStyle"] == "pill"
    assert pill["data"]["visual"]["italic"] is True
    assert note["zIndex"] == _Z_NOTE  # notes float above


def test_apply_geanz_styling_noop_on_generic():
    nodes = [_node("Payroll", visual={"bgColor": "#b5ffff"})]
    assert apply_geanz_styling(nodes) is False
    assert "borderRadius" not in nodes[0]["data"]["visual"]  # untouched


def test_apply_geanz_styling_idempotent():
    nodes = [_node("Strategy (theme)", qualifier="CBC Themes", visual={"bgColor": "#ffffff"})]
    apply_geanz_styling(nodes)
    first = dict(nodes[0]["data"]["visual"])
    apply_geanz_styling(nodes)
    assert nodes[0]["data"]["visual"] == first
