# ADR-203: KG skips redundant set → element edges for packaged elements

Status: Accepted (2026-05-18)
Extends: [ADR-199](ADR-199-KG-Settings-Tab-Split-And-Element-Package-Edge.md)

## Context

Issue [#181](https://github.com/cgbarlow/iris/issues/181) — on the
knowledge graph view, the user wants the chain `set → package →
element`, not the direct `set → element` edge for elements that
already belong to a package.

Background. ADR-199 (v6.9.0) added the `element_package` edge type
so packages render as containers of their elements. But the graph
service kept emitting the existing `set_membership` edge from
`set → element` *unconditionally*, so a packaged element ended up
with two paths from its set:

```
set ──────────────────────► element   (set_membership, ADR-184)
 │                            ▲
 └─► package ─────────────────┘       (set_membership + element_package, ADR-199)
```

That's redundant clutter. The set → package → element chain
conveys the containment more usefully and the direct edge adds
no information for a packaged element.

The user explicitly asked whether a new toggle was needed.

## Decision

Skip the direct `set → element` edge whenever the element has a
`package_id` that is **visible in the current scope** (i.e. the
package is in `package_ids`). No new toggle.

Implementation: one `if pkg_id and pkg_id in package_ids: continue`
guard at the top of the existing `set_membership` element loop in
`get_graph_data`.

### Why no toggle

- The redundant edge is visual noise — every user benefits from
  the cleaner default.
- The information is preserved: the chain `set → package → element`
  is still there.
- Toggle proliferation is its own cost. A toggle implies "some
  users will want this on, some off"; here the answer is "almost
  everyone wants the cleaner view".
- If a future user genuinely needs the direct edge, they can hide
  the `element_package` and `package` toggles and the set →
  element edges will still be there for un-packaged elements;
  packaged elements would then surface their containment via the
  `set → package` chain (with packages hidden, they'd look
  orphaned — but that's the user's explicit choice).

Trivially reversible: the rule is one `continue` statement. If
the call comes for a toggle, add it; until then, simpler.

### Why "visible in the current scope" rather than unconditional

If an element has a `package_id` pointing to a package that's
*not* in the current scope (e.g. soft-deleted, or in a different
set when the graph is scoped to a single set), removing the
direct set → element edge would visually orphan the element —
neither the chain nor the direct edge would render. The guard
`pkg_id in package_ids` ensures we only skip the direct edge
when the chain actually exists.

## Why no migration / schema change

Pure read-path filtering. No data is added or removed; the
`element.package_id` column the rule reads has been there since
ADR-184. The element_package edge type registered in ADR-199 is
unchanged.

## Consequences

- `backend/app/graph/service.py:368-377` — three-line guard
  before the existing element `set_membership` loop.
- `backend/tests/test_graph/test_element_package_edges.py` — one
  new test (`test_no_redundant_set_membership_when_element_packaged`)
  asserts the rule and the surviving `set → package` and
  `package → element` edges. The 4 prior tests still pass
  (they didn't exercise this combination).
- No frontend change — the front end just renders what the
  backend emits.
- No migration, no MCP / CLI change.
- CHANGELOG `[6.12.0]`. Minor bump because it changes user-
  visible graph rendering for any set that has packaged elements.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_graph/
```

31 green.

Manual smoke: open KG for a set containing both free-floating
elements and elements assigned to packages. Confirm:
- Free-floating elements still show a direct `set → element` edge.
- Packaged elements are reached only via `set → package → element`.
- Toggling `element_package` off (in the new Relationships tab)
  hides the chain; packaged elements then look set-less in the
  graph. That's the documented trade-off.

## See also

- Issue [#181](https://github.com/cgbarlow/iris/issues/181).
- [ADR-199](ADR-199-KG-Settings-Tab-Split-And-Element-Package-Edge.md)
  — the `element_package` edge type this ADR builds on.
- [ADR-184](ADR-184-Element-Package-Membership.md) — the
  `element.package_id` column underpinning both edges.
