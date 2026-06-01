"""ADR-231: importing the GEANZ Common Business Capabilities XMI preserves
the nestedClassifier element-containment tree (capability zone → capability
→ sub-capability) as ``elements.parent_element_id`` links.

Uses the real committed GEANZ model at the repo root. Idempotent re-import
back-fills links without duplicating elements.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.import_sparx_xml.service import import_sparx_xml_file

from .conftest import admin_user_id, auth_headers

if TYPE_CHECKING:
    import httpx

GEANZ_XML = (
    Path(__file__).resolve().parents[3]
    / "GEANZ Common Business Capabilities Sparx EA model.xml"
)


async def _count(db, sql: str) -> int:  # noqa: ANN001
    cursor = await db.execute(sql)
    return (await cursor.fetchone())[0]


async def _count_p(db, sql: str, params: tuple) -> int:  # noqa: ANN001
    cursor = await db.execute(sql, params)
    return (await cursor.fetchone())[0]


class TestGeanzContainment:
    async def test_nested_classifier_tree_imported(self, client: httpx.AsyncClient) -> None:
        await auth_headers(client)  # ensures the admin user exists
        uid = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        summary = await import_sparx_xml_file(db, str(GEANZ_XML), imported_by=uid)
        assert summary.elements_created > 100, summary

        # Many elements are nested (capabilities under zones, sub-caps under caps).
        nested = await _count(
            db, "SELECT COUNT(*) FROM elements WHERE parent_element_id IS NOT NULL "
            "AND is_deleted = 0",
        )
        assert nested > 100, f"expected a deep tree, only {nested} nested elements"

        # Depth reaches 3 levels: a sub-capability → capability → zone (root).
        three_deep = await _count(
            db,
            "SELECT COUNT(*) FROM elements e3 "
            "JOIN elements e2 ON e3.parent_element_id = e2.id "
            "JOIN elements e1 ON e2.parent_element_id = e1.id "
            "WHERE e1.parent_element_id IS NULL AND e3.is_deleted = 0",
        )
        assert three_deep > 0, "no 3-level zone→capability→sub-capability chain found"

        # A known zone owns children.
        zone_kids = await _count(
            db,
            "SELECT COUNT(*) FROM elements c "
            "JOIN elements z ON c.parent_element_id = z.id "
            "JOIN element_versions zv ON z.id = zv.element_id AND z.current_version = zv.version "
            "WHERE zv.name = 'Customer Service Delivery capability zone' "
            "AND c.is_deleted = 0",
        )
        assert zone_kids > 0, "the CCS.00 zone has no child capabilities"

    async def test_reimport_into_same_set_is_idempotent(self, client: httpx.AsyncClient) -> None:
        """Re-importing into the SAME set dedups by ea_guid (no duplicate
        elements) and the parent-link post-process is stable (same links)."""
        headers = await auth_headers(client)
        uid = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]

        resp = await client.post("/api/sets", json={"name": "GEANZ"}, headers=headers)
        set_id = resp.json()["id"]

        await import_sparx_xml_file(db, str(GEANZ_XML), imported_by=uid, set_id=set_id)
        in_set = "WHERE set_id = ? AND is_deleted = 0"
        elems_1 = await _count_p(db, f"SELECT COUNT(*) FROM elements {in_set}", (set_id,))
        nested_1 = await _count_p(
            db, f"SELECT COUNT(*) FROM elements {in_set} AND parent_element_id IS NOT NULL",
            (set_id,),
        )
        assert nested_1 > 100, nested_1

        await import_sparx_xml_file(db, str(GEANZ_XML), imported_by=uid, set_id=set_id)
        elems_2 = await _count_p(db, f"SELECT COUNT(*) FROM elements {in_set}", (set_id,))
        nested_2 = await _count_p(
            db, f"SELECT COUNT(*) FROM elements {in_set} AND parent_element_id IS NOT NULL",
            (set_id,),
        )

        assert elems_2 == elems_1, f"re-import duplicated elements: {elems_1} -> {elems_2}"
        assert nested_2 == nested_1

    async def test_hierarchy_surfaces_nested_elements(self, client: httpx.AsyncClient) -> None:
        """get_diagram_hierarchy nests element nodes under their parent element
        / package, reaching the 3-level GEANZ depth (ADR-231 E5)."""
        from app.diagrams.service import get_diagram_hierarchy

        headers = await auth_headers(client)
        uid = await admin_user_id(client)
        db = client._transport.app.state.db_manager.main_db  # type: ignore[union-attr]
        resp = await client.post("/api/sets", json={"name": "GEANZ"}, headers=headers)
        set_id = resp.json()["id"]
        await import_sparx_xml_file(db, str(GEANZ_XML), imported_by=uid, set_id=set_id)

        tree = await get_diagram_hierarchy(db, set_id=set_id)

        def max_element_depth(nodes: list, depth: int = 0) -> int:
            best = depth
            for n in nodes:
                d = depth + (1 if n["node_type"] == "element" else 0)
                best = max(best, d, max_element_depth(n["children"], d))
            return best

        # zone(1) → capability(2) → sub-capability(3).
        assert max_element_depth(tree) >= 3, "element containment not nested 3 deep in tree"

        # At least one element node has element children.
        def has_nested_element(nodes: list) -> bool:
            for n in nodes:
                if n["node_type"] == "element" and any(
                    c["node_type"] == "element" for c in n["children"]
                ):
                    return True
                if has_nested_element(n["children"]):
                    return True
            return False

        assert has_nested_element(tree)
