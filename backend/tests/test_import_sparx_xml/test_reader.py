"""Unit tests for the Sparx EA native XMI reader (no DB)."""

from __future__ import annotations

import os

from app.import_sparx.converter import ea_rect_to_position
from app.import_sparx_xml.reader import is_sparx_xmi_file, parse_sparx_xmi

SAMPLE_XMI = os.path.join(os.path.dirname(__file__), "sample_ea_xmi.xml")
# An ArchiMate OEX file (Open Group namespace) — must NOT sniff as Sparx XMI.
OEX_SAMPLE = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "docs", "reference", "ArchiMate", "sample-with-view.xml",
)


class TestSniff:
    def test_accepts_sparx_xmi(self) -> None:
        assert is_sparx_xmi_file(SAMPLE_XMI) is True

    def test_rejects_archimate_oex(self) -> None:
        assert is_sparx_xmi_file(os.path.abspath(OEX_SAMPLE)) is False

    def test_rejects_missing_file(self) -> None:
        assert is_sparx_xmi_file("/no/such/file.xml") is False


class TestParse:
    def test_packages(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        assert len(model.packages) == 1
        pkg = model.packages[0]
        assert pkg.Package_ID == 1
        assert pkg.Name == "Sample Package"
        # Parent EAPK_ROOT is outside the export → resolves to root (0).
        assert pkg.Parent_ID == 0
        assert pkg.ea_guid == "EAPK_PKG1"

    def test_elements(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        assert len(model.elements) == 3
        by_id = {e.Object_ID: e for e in model.elements}

        cap = by_id[10]
        assert cap.Object_Type == "Class"
        assert cap.Stereotype == "ArchiMate_Capability"
        assert cap.Alias == "CAP.A"
        assert cap.Package_ID == 1
        assert cap.Backcolor == 16708300
        assert cap.Bordercolor == 14772545
        assert cap.BorderWidth == 3
        assert cap.ea_guid == "EAID_A"

        abstract_c = by_id[12]
        assert abstract_c.Abstract == "1"

    def test_connectors(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        assert len(model.connectors) == 1
        conn = model.connectors[0]
        assert conn.Connector_ID == 100
        assert conn.Connector_Type == "Association"
        assert conn.Stereotype == "ArchiMate_Association"
        assert conn.Start_Object_ID == 10
        assert conn.End_Object_ID == 11

    def test_diagram(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        assert len(model.diagrams) == 1
        diag = model.diagrams[0]
        assert diag.Diagram_ID == 200
        assert diag.Diagram_Type == "Logical"
        assert diag.Package_ID == 1
        assert diag.cx == 1138
        assert diag.cy == 795

    def test_diagram_objects_and_geometry(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        assert len(model.diagram_objects) == 2
        node_a = next(o for o in model.diagram_objects if o.Object_ID == 10)
        # XMI Left=10;Top=20;Right=130;Bottom=80 → normalised to .qea convention.
        assert node_a.RectLeft == 10
        assert node_a.RectRight == 130
        assert node_a.RectTop == -20
        assert node_a.RectBottom == -80
        # And it must round-trip through the existing converter to screen coords.
        pos = ea_rect_to_position(
            node_a.RectLeft, node_a.RectRight, node_a.RectTop, node_a.RectBottom
        )
        assert pos == {"x": 10, "y": 20, "width": 120, "height": 60}

    def test_diagram_links(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        assert len(model.diagram_links) == 1
        link = model.diagram_links[0]
        assert link.DiagramID == 200
        assert link.ConnectorID == 100

    def test_tagged_values(self) -> None:
        model = parse_sparx_xmi(SAMPLE_XMI)
        tvs = [t for t in model.tagged_values if t.Object_ID == 10]
        assert len(tvs) == 1
        assert tvs[0].Property == "Current Maturity Level"
        assert tvs[0].Value == "3"
