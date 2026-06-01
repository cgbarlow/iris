# SPEC-231-A: Element → element containment

Implements **[ADR-231](../ADR-231-Element-Element-Containment.md)**. Living
document. v1 scope = **import + browse** (set parent on create/update; no
drag-to-reparent).

## Schema delta

```sql
-- SQLite m081 (PRAGMA-guarded) / Supabase m087 (IF NOT EXISTS)
ALTER TABLE elements ADD COLUMN parent_element_id TEXT REFERENCES elements(id);
CREATE INDEX idx_elements_parent_element ON elements(parent_element_id);
```
Nullable, additive, no back-fill. `parent_element_id` is unversioned (carried
on the `elements` row, like `package_id` / `detail_diagram_id`).

## Placement precedence (single source of truth — hierarchy builder)
```
if element.parent_element_id:  parent = that element        # node_type 'element'
elif element.package_id:       parent = that package        # today's behaviour
else:                          loose under set_id
```

## Invariants (service → 422, `ElementParentInvariantError`)
- parent row exists and `is_deleted = 0`;
- `parent.set_id == child.effective set_id` (single-set);
- no cycle (walk `parent_element_id` up from the proposed parent; reject if
  it reaches the child); reject `parent_element_id == id` (self-parent).

## API surface
| Verb | Backend | MCP | CLI | Note |
|---|---|---|---|---|
| create w/ parent | `POST /api/elements` (`parent_element_id`) | `create_element(parent_element_id?)` | `element create --parent-element-id` | enrichment |
| update parent | `PUT /api/elements/{id}` (tri-state `parent_element_id`) | `update_element(parent_element_id?)` | `element update --parent-element-id` | enrichment |
| children (read) | `GET /api/elements/{id}/children` | — | — | GET, not §14 |
| ancestors (read) | `GET /api/elements/{id}/ancestors` | — | — | GET, breadcrumb |

`ElementResponse` gains `parent_element_id` + `parent_element_name`. No
`move_element` (ADR-178 untouched).

## Importer mapping
For each XMI `<element>` `<model owner="GUID">`:
`parent_obj_id = guid_to_int[owner] if owner and owner != package_guid else None`
(the `!= package` test discards the EAPK/root case; `element_map` discards a
stray non-element owner). Carried on `QeaElement.Parent_Object_ID`; applied in
an idempotent post-process `UPDATE elements SET parent_element_id=?` keyed off
`element_map` (handles parent-after-child ordering). `package_id` wiring
unchanged.

## Hierarchy
`get_diagram_hierarchy` gains a UNION arm: elements with `parent_element_id IS
NOT NULL` OR that are themselves a parent → `node_type:'element'`, parent key
`COALESCE(parent_element_id, package_id)`. `DiagramHierarchyNode.node_type` →
`'package'|'diagram'|'element'`. `get_package_hierarchy(include_elements=False)`
opt-in for the MCP orient path.

## Acceptance criteria
- **AC1** column + index present (SQLite + Supabase schema test).
- **AC2** create with `parent_element_id` sets it; `get`/`list` return it + `parent_element_name`.
- **AC3** invariants reject missing/soft-deleted/cross-set parent, cycle, self → 422.
- **AC4** `update` tri-state: set / clear via `null` / omit = untouched.
- **AC5** `GET /{id}/children` + `/{id}/ancestors`.
- **AC6** importer: `<model owner=EAID>` → `parent_element_id` set; `owner=EAPK` (root) → NULL; idempotent re-import.
- **AC7** `get_diagram_hierarchy` returns the GEANZ zone→capability→sub-capability subtree 3 deep; node count matches the XMI `owner=EAID` count.
- **AC8** MCP + CLI round-trip `parent_element_id` on create + update; `check_surface_parity.py` green.
- **AC9** Frontend: nested elements render in `TreeNode`; element page shows parent link + child list.

## Files
Backend: `migrations/m081_*.py` + `supabase/m087_*.sql` + `tests/test_migrations/test_element_parent_element_schema.py`; `elements/{service,models,router}.py`; `import_sparx/{reader,service}.py`; `import_sparx_xml/reader.py`; `diagrams/service.py`; `packages/service.py` (port cycle/ancestors); `startup.py`. MCP `iris_mcp/tools.py`; CLI `iris_cli/main.py`. Frontend `lib/types/api.ts`, `lib/components/TreeNode.svelte`, `routes/elements/[id]/+page.svelte`.

## Out of scope (deferred)
Drag-to-reparent UI + `move_element` / `PUT /api/elements/{id}/parent` (needs a new ADR amending ADR-178). Package-detail nested rendering.
