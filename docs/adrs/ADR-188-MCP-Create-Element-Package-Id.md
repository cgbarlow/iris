# ADR-188: MCP `create_element` accepts `package_id`

Status: Accepted (2026-05-16)
Extends: [ADR-184](ADR-184-Element-Package-Membership.md) (element→package membership)
Relates to: [ADR-182](ADR-182-Surface-Parity-Discipline.md) (surface parity)

## Context

Issue [#154](https://github.com/cgbarlow/iris/issues/154) — "create_element
doesn't take a package_id directly." When v6.7.0 introduced
element→package membership (ADR-184), the REST `POST /api/elements`
body and the CLI `create_element` subcommand both gained a
`package_id` field, but the MCP `create_element` tool did not. MCP
clients had to call `create_element` and then follow up with
`update_element` to attach the new element to a package — two round
trips for the most common authoring workflow.

This is a surface-parity gap under Protocol §14 / ADR-182, even
though the parity-check script — which compares verb/entity tuples
rather than per-parameter signatures — flagged nothing.

## Decision

Add an optional `package_id` parameter to the MCP `create_element`
tool. The MCP handler forwards a non-null `package_id` into the POST
body to `/api/elements`; the backend already validates that the
package belongs to the same set as `set_id` (the same invariant the
update path enforces).

```
"package_id": _str_arg(
    "package_id",
    "Optional package to attach the new element to (v6.7.4, ADR-188 /
     issue #154). The package must belong to the same set as set_id;
     otherwise the REST call returns 400. Saves a follow-up
     update_element call.",
    required=False,
),
```

Omitted and explicit-`None` are treated identically and dropped from
the body — `create_element` has no tri-state semantics (unlike
`update_element`, which uses `None` to mean "clear the membership").

## Why not introduce a tri-state on create

There's nothing to "clear" on a brand-new element. The field is
either set or absent; symmetry with `update_element` would add
complexity without expressing any new state.

## Why not require a CLI / REST change

Both already accept `package_id`. The gap is entirely on the MCP
surface.

## Consequences

- `mcp/src/iris_mcp/tools.py` — `create_element` schema gains
  `package_id`; the handler appends `"package_id"` to the body-key
  loop.
- `mcp/tests/test_create_element_package.py` — new file mirroring
  `test_update_element_package.py`. Asserts the schema property, body
  forwarding, and that omission / `None` both drop the field.
- No migration required.
- No `scripts/check_surface_parity.py` change required — parity is
  enforced at the verb/entity level, and `(create, element)` was
  already present on all three surfaces.
- CHANGELOG `[6.7.4]`.

## Verification

- `pytest mcp/tests/test_create_element_package.py` — four tests, all
  green.
- Manual MCP smoke (during the dev.sh smoke step): call
  `create_element` with `set_id` and `package_id` set; confirm the
  returned `package_id` matches and that no follow-up `update_element`
  is needed.
- `python scripts/check_surface_parity.py` — unchanged (green).

## See also

- [ADR-184](ADR-184-Element-Package-Membership.md) — origin of the
  `package_id` column on elements and the cross-set validation rule.
- [ADR-182](ADR-182-Surface-Parity-Discipline.md) — parity discipline.
- Issue [#154](https://github.com/cgbarlow/iris/issues/154).
