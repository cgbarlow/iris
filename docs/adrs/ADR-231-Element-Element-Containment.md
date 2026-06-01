# ADR-231: Element → element optional containment (nested elements)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-231 |
| **Initiative** | Import the GEANZ capability tree (and any Sparx EA nested-classifier model) with its full depth, as a navigable element hierarchy |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** importing Sparx EA models whose structure is an
element-containment tree — the GEANZ Common Business Capabilities model
(`set_id=7f2521de…`) nests *capability zone → capability → sub-capability*
three levels deep, encoded in the XMI as `<nestedClassifier>` where each
`<element>`'s `<model>` carries both `package="EAPK_…"` (its containing
package) and `owner="EAID_…"` (its parent **element**),

**facing** that Iris has no element→element containment. An element can
belong to a **package** (ADR-184, the single nullable `elements.package_id`
column — something EA lacks) and can drill to a **detail diagram** (ADR-221,
`elements.detail_diagram_id`), but there is no way for an element to *own*
child elements. The XMI importer (`backend/app/import_sparx_xml/reader.py`,
Pass 2) reads each element's `<model package>` but **drops `<model owner>`**
(the diagram path already reads `owner` for ADR-221 detail diagrams — the
element path does not). So all ~394 GEANZ capability classes flatten under
the top `CBC` package and the live set shows only `CBC → CBC Themes` — the
3-level tree the EA Project Browser shows is lost. Re-importing reproduces
this; it is a data-model gap, not a one-off,

**we decided to** add a new **optional element-containment axis** —
a nullable `elements.parent_element_id TEXT REFERENCES elements(id)` column,
mirroring how `package_id` was added in ADR-184 — and wire it through the
importer, the navigable hierarchy, and the element/MCP/CLI surfaces:

  - **(E1) Schema.** `parent_element_id` + `idx_elements_parent_element`,
    shipped as a paired SQLite (`m081`) + Supabase (`m087`) migration with a
    schema-parity test (§15). Additive, nullable, no back-fill.

  - **(E2) Two orthogonal axes, one placement rule.** An element row can
    now carry both `package_id` (→package, ADR-184) and `parent_element_id`
    (→element, this ADR). They are orthogonal. The **navigable tree
    placement precedence** is defined **once**, in the hierarchy builder
    (DRY §13): (1) if `parent_element_id` is set → the element is a child of
    that element; (2) else if `package_id` is set → under that package
    (today's behaviour); (3) else → loose under `set_id`. `package_id` is
    **kept** (not cleared) on a nested element — it remains meaningful EA
    data and ADR-184's set-consistency invariant still applies; the builder
    simply prefers `parent_element_id` for placement.

  - **(E3) Invariants** (service layer → HTTP 422, mirroring
    `ElementPackageInvariantError`): the parent must exist and be
    non-deleted; the child's effective `set_id` must equal the parent's
    `set_id` (**single-set containment** — unlike the cross-set ADR-221
    detail link, a structural tree must not span sets); no cycles (the
    `validate_no_cycle` walk-up from `packages/service.py` ported to
    elements); no self-parent.

  - **(E4) Importer.** Read `<model owner>` in
    `import_sparx_xml/reader.py` (mirroring the diagram `owner` logic),
    carry it on `QeaElement.Parent_Object_ID`, and set `parent_element_id`
    in an idempotent **post-process pass** in `import_sparx/service.py`
    (parent elements may be created after their children — same reason the
    ADR-221 detail-diagram link is post-processed). Re-import is the
    canonical back-fill for the existing flat set.

  - **(E5) Navigable hierarchy.** Extend `get_diagram_hierarchy` to emit
    nested elements as `node_type:'element'` nodes (attaching via
    `COALESCE(parent_element_id, package_id)`), reusing the existing
    `DiagramHierarchyNode` model and `TreeNode.svelte` recursion. Add an
    opt-in `include_elements` flag to `get_package_hierarchy` (ADR-158) so
    the MCP `package_hierarchy` orient sheet can show depth — default off.

  - **(E6) Write surface — an update, not a move.** `parent_element_id` is
    set via the existing `create_element` / `update_element` verbs (exactly
    the ADR-184 `package_id` precedent), exposed on backend + MCP + CLI. **No
    `move_element` verb is added** — so ADR-178's forbidden-asymmetry
    catalogue and `check_surface_parity.py` are untouched. Manual
    drag-to-reparent is explicitly deferred to a later ADR.

**because** the GEANZ depth is genuine element containment, not package
nesting (the zones are rich elements — notes, maturity tagged values, their
own CCS.00-style diagrams — so turning them into packages would be lossy),
the `owner` linkage is already present in the XMI and merely discarded, and
a nullable parent column reuses the proven `package_id`/`parent_package_id`
patterns while keeping package membership and element containment as clean,
independent axes.

---

## Consequences

**Positive**
- Sparx EA nested-classifier models (GEANZ and others) import with full
  depth and render as a browsable tree in the existing nav sidebar.
- Zones/capabilities remain first-class elements; nothing about ADR-184 or
  ADR-221 changes — the new axis is additive and orthogonal.
- No new write verb, no new parity entity, no ADR-178 amendment.

**Negative / risks**
- A third membership axis on the element row; the precedence rule must live
  in exactly one place (the hierarchy builder) to avoid drift.
- The existing flat GEANZ set stays flat until re-imported (the column has
  no back-fill).
- The hierarchy UNION must be scoped to containment-involved elements so it
  does not pull the entire flat element pool into every package.

## Alternatives considered
1. **Map container elements to nested packages** (reuse `parent_package_id`).
   Rejected: a capability zone would become a package, losing its element
   identity/notes/maturity/own diagram, or be duplicated as both.
2. **Reuse `package_id` for the tree.** Rejected: a different axis; would
   conflate package membership with structural containment.
3. **Detail-diagram drill-down only (ADR-221).** Rejected: navigation via
   diagrams, not a browsable element tree; GEANZ uses nested classifiers,
   not composite diagrams.
4. **Many-to-many containment (join table).** Rejected: containment is a
   tree; a single nullable column mirrors `package_id` and suffices.
5. **Cross-set containment.** Rejected: keeps trees single-set and the
   hierarchy query simple.

## Surface parity (§14)
`parent_element_id` enriches the existing `create_element` / `update_element`
write verbs on all three surfaces — no new entity, no new exception, no
`move_element`. `scripts/check_surface_parity.py` stays green unchanged.

## SQLite ↔ Supabase parity (§15)
Paired `m081` (SQLite) + `m087` (Supabase) migrations, both idempotent
(`IF NOT EXISTS` / PRAGMA guard), with `test_element_parent_element_schema.py`.
No boolean columns. Both run at startup (`startup.py`).

## Dependencies
Extends **ADR-184** (element-package membership) with a sibling axis;
consistent with **ADR-178** (no element move) and **ADR-221** (detail
diagram). Spec: `docs/adrs/specs/SPEC-231-A-Element-Element-Containment.md`.
