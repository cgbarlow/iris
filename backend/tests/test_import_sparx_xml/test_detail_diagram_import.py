"""ADR-221: Sparx EA composite elements import as element → detail diagram
drill links.

A diagram whose ``<model owner="...">`` is an element (rather than its
containing package) is a "composite" child diagram. The reader records
the owning element's int id as ``QeaDiagram.ParentID``; the orchestrator
sets that element's ``detail_diagram_id`` to the imported diagram.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.import_sparx_xml.reader import parse_sparx_xmi
from app.import_sparx_xml.service import import_sparx_xml_file

from .conftest import auth_headers

if TYPE_CHECKING:
    import httpx

COMPOSITE_XMI = os.path.join(os.path.dirname(__file__), "sample_ea_xmi_composite.xml")


class TestReader:
    def test_composite_diagram_records_owning_element_as_parent(self) -> None:
        model = parse_sparx_xmi(COMPOSITE_XMI)
        diagrams = {d.Name: d for d in model.diagrams}
        detail = diagrams["Capability A Detail"]
        # The owner GUID EAID_A interns to the element's ea_localid (10).
        assert detail.ParentID == 10

    def test_package_owned_diagram_has_no_parent(self) -> None:
        # The stock sample diagram is owned by its package → not composite.
        stock = parse_sparx_xmi(
            os.path.join(os.path.dirname(__file__), "sample_ea_xmi.xml"),
        )
        sample_diag = next(d for d in stock.diagrams if d.Name == "Sample Diagram")
        assert sample_diag.ParentID is None


class TestOrchestrator:
    async def test_import_populates_detail_diagram_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        await auth_headers(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        user_id = (await cursor.fetchone())[0]

        await import_sparx_xml_file(db, COMPOSITE_XMI, imported_by=user_id)

        # Element "Capability A" should now point at the imported detail diagram.
        cursor = await db.execute(
            "SELECT e.id, e.detail_diagram_id FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id "
            "  AND e.current_version = ev.version "
            "WHERE ev.name = 'Capability A' AND e.is_deleted = 0",
        )
        elem_row = await cursor.fetchone()
        assert elem_row is not None
        detail_id = elem_row[1]
        assert detail_id is not None, "detail_diagram_id was not populated"

        # And that id resolves to the composite diagram.
        cursor = await db.execute(
            "SELECT dv.name FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id "
            "  AND d.current_version = dv.version "
            "WHERE d.id = ?",
            (detail_id,),
        )
        diag_row = await cursor.fetchone()
        assert diag_row is not None
        assert diag_row[0] == "Capability A Detail"
