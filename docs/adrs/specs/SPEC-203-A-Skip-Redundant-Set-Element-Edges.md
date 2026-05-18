# SPEC-203-A: Skip redundant set → element edges for packaged elements

Implements: [ADR-203](../ADR-203-Skip-Redundant-Set-Element-Edges-For-Packaged.md)
Resolves: Issue [#181](https://github.com/cgbarlow/iris/issues/181)
Status: Living

## Emission rule

In `backend/app/graph/service.py:get_graph_data`, the element
`set_membership` loop now skips elements whose `package_id` resolves
to a visible package in the current scope:

```python
for row in element_rows:
    eid, sid, pkg_id = row[0], row[4], row[5]
    if pkg_id and pkg_id in package_ids:
        continue   # ADR-203: chain via package, skip direct edge.
    if sid and sid in set_ids:
        edges.append({...edge_type: "set_membership"...})
```

The `element_package` emission (ADR-199) is unchanged — it always
fires when the element has a visible package.

## Resulting graph shapes

| Element state | set → element | set → package | package → element |
|---|:-:|:-:|:-:|
| Free-floating (`package_id IS NULL`) | ✅ | n/a | n/a |
| Packaged, package in scope | ❌ (this PR) | ✅ | ✅ |
| Packaged, package out of scope | ✅ (fallback) | n/a | n/a |

## Acceptance criteria

1. A graph fetched for a set containing both free-floating and
   packaged elements renders direct `set_membership` edges only
   for the free-floating ones.
2. Packaged elements appear via `set → package` + `package →
   element` chain (two edges).
3. An element whose `package_id` references a package outside the
   current scope (e.g. the package is soft-deleted) still gets
   its direct `set → element` edge so it isn't visually orphaned.
4. No other edge types are affected. The `set_membership` edges
   from set → diagram and set → package are unchanged.

## Tests

`backend/tests/test_graph/test_element_package_edges.py`:

- `test_no_redundant_set_membership_when_element_packaged` — new.
  Asserts the free-floating element keeps its set→element edge,
  the packaged element does not, the set→package edge for the
  packaging package is still present, and the package→element
  chain exists.

- All 4 prior tests in the module continue to pass — they
  cover defaults, edge emission for packaged elements, no-edge
  when un-packaged, and node typing.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_graph/
```

All 31 green.

Manual smoke per ADR-203 verification section.
