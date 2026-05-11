# ADR-153: Drop redundant `iris:` prefix from MCP prompt names

Status: Accepted (2026-05-11)
Amends: [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md)

## Context

ADR-152 chose the prompt name format `iris:set:<uuid>` and
`iris:collection:<uuid>` for scope system prompts exposed via the MCP
`prompts` capability. The `iris:` prefix was added defensively, to
namespace the prompts under the Iris MCP server.

Post-v5.8.3 empirical evidence from Claude Code's slash menu shows
that **MCP clients prepend the server name to every prompt entry
automatically.** In Claude Code's slash picker the v5.8.3 prompt
appears as:

```
/iris:iris:set:33032180-d77a-4ce4-88cf-b49cd643e093
```

The first `iris:` comes from the client prepending the MCP server name
(`iris`); the second `iris:` is the prefix ADR-152 added to the prompt
name. The result is a redundant doubled prefix that's visible in the
slash UI of every MCP client.

This is a small but real UX paper-cut on what's otherwise the
spec-compliant invocation path the v5.8.x rollout is built around. The
namespace ADR-152 wanted to provide is already provided by the MCP
client out of the box, via the server name.

## Decision

**Drop the `iris:` prefix from prompt names.** The new format is:

- `set:<uuid>` (was: `iris:set:<uuid>`)
- `collection:<uuid>` (was: `iris:collection:<uuid>`)

MCP clients namespace these under their server identity automatically;
in Claude Code's slash menu the prompt appears as `/iris:set:<uuid>`,
cleanly. The `<scope_type>:<uuid>` shape remains stable across
renames, exports, and re-imports — that property is unchanged.

This is the only modification to ADR-152's naming decision. Body
shape (`role: user` single message + provenance preamble + system
prompt body), name regex anchoring, error semantics, capability
declaration, and the dedicated backend index endpoint are all
unchanged.

## Why drop rather than keep

- **Empirical UX evidence.** Doubled-prefix is visible in real Claude
  Code usage today and unavoidable as long as the server name is
  `iris`. Renaming the server would break every existing client
  config — far worse than renaming the prompt format.
- **No backwards-compat cost.** The only consumers of prompt names
  are MCP clients enumerating prompts. They re-enumerate on every
  `prompts/list` call. There is no stored URI corpus to migrate.
- **The namespace was always implicit.** A prompt named
  `iris:set:<uuid>` cannot exist *outside* the `iris` MCP server's
  enumeration anyway — the URI lives inside that server's namespace
  by construction. Adding `iris:` to the URI was belt-and-braces on
  something already covered by the spec.

## Consequences

- One-line change in `backend/app/prompts/service.py` to emit the
  shorter name.
- One-line regex change in `mcp/src/iris_mcp/prompts.py` to accept
  the shorter name.
- Test fixtures across backend / iris-client / MCP get the prefix
  stripped — mechanical.
- SPEC-152-A updated since specs are living docs.
- Any user who copy-pasted a v5.8.3-formatted prompt name into
  external automation will need to drop the `iris:` prefix. Unlikely
  to exist in practice given v5.8.3 only shipped 36 hours ago and
  the field is enumerable.

## Why an ADR amendment rather than editing ADR-152

ADR-152 is approved and per project protocol #1 stays immutable.
ADR-153 records this naming refinement explicitly so the audit trail
shows: "we chose X, then empirical evidence revealed a UX issue, we
chose X-prime." Cleaner than retroactively rewriting ADR-152.

## See also

- [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md)
  — the original decision being amended.
- [SPEC-152-A](specs/SPEC-152-A-MCP-Prompts-Capability.md) — updated
  to reflect the new naming as the living source of truth.
