# SPEC-235-A: Composite diagram → element nesting via the EA `parent` attribute

Implements **[ADR-235](../ADR-235-Composite-Diagram-Element-Nesting.md)**
(builds on ADR-221, ADR-231, ADR-232).

## Root cause
In the GEANZ XMI every `<diagram><model>` has:
- `owner` = the **root package** GUID (where the diagram is *filed*), and
- `parent` = the **element** GUID it is the composite child-diagram of.

The reader only consulted `owner`, and because `owner == package` for all 40
diagrams the ADR-221 composite link (`owner != package`) never fired, so
`detail_diagram_id` stayed NULL and the hierarchy filed every diagram flat
under the root package. 39/40 diagrams carry `parent="EAID_…"`; the 1 without
is the top-level "Common Business Capabilities - capability zones" map.

## Change — `backend/app/import_sparx_xml/reader.py` (pass 4: diagrams)
Derive the diagram's `ParentID` from `parent` first, then fall back to a
non-package `owner`:

```python
owner_guid = m.get("owner") if m is not None else None
parent_guid = m.get("parent") if m is not None else None
parent_ref = parent_guid or (
    owner_guid if owner_guid and owner_guid != pkg_guid else None
)
parent_id = guid_to_int.get(parent_ref) if parent_ref else None
```

`guid_to_int` already interns every EA-extension `<element idref>` (pass 1),
so the `parent` element GUID resolves to its synthetic int id.

## Downstream (unchanged — reused)
- `backend/app/import_sparx/service.py` **step 7** maps `diag.ParentID` →
  `element_map` → sets `elements.detail_diagram_id` (idempotent; back-fills on
  re-import of the same set).
- `backend/app/diagrams/service.py` `get_diagram_hierarchy` diagram UNION arm
  already nests a diagram under the element whose `detail_diagram_id` matches
  (`COALESCE(<owning element id>, d.parent_package_id)`).

## Tests — `backend/tests/test_import_sparx_xml/test_geanz_containment.py`
`test_capability_diagrams_nest_under_their_element`:
- ≥30 elements get a non-null `detail_diagram_id` after import;
- a diagram node appears as a **child of an element node** in
  `get_diagram_hierarchy`;
- concretely the **Payroll** element owns the "CCO.08 Payroll capability area"
  diagram as a child;
- ≤5 diagrams remain directly under any package (only genuine root maps).

## Verification
Backend: `pytest tests/test_import_sparx_xml/test_geanz_containment.py` (6/6).
No schema, no endpoint, no MCP/CLI surface change → `check_surface_parity.py`
unaffected, no migration. Existing sets need a **re-import** to pick up the
links.
