# ADR-244: Cap the MCP Python SDK below 2.x for iris-mcp

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-244 |
| **Initiative** | Restore the `iris-mcp` Render service, which crashed at startup on the v6.48.0 deploy |
| **Proposed By** | Engineering |
| **Date** | 2026-09-16 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the standalone `iris-mcp` service (ADR-134), whose image is
built by `mcp/Dockerfile` with a plain `pip install ./iris-client ./mcp` — **no
lockfile** — against `mcp/pyproject.toml`, which declared `mcp>=1.2` with no upper
bound, and whose server wiring (`iris_mcp.server.build_server`) is written against
the SDK 1.x low-level `Server` decorator API (`@server.list_tools()`,
`call_tool`, `list_resources`, `read_resource`, `list_prompts`, `get_prompt`),

**facing** the v6.48.0 deploy (a version bump invalidated the Docker layer cache, so
dependencies re-resolved) installing **`mcp` 2.2.0**, which no longer exposes
those decorators; the service exited at boot with
`AttributeError: 'Server' object has no attribute 'list_tools'` (reproduced locally
with the same Dockerfile),

**we decided to** cap the dependency at **`mcp>=1.2,<2`** (resolves to 1.30.0 today)
and add a guard test (`mcp/tests/test_sdk_version_pin.py`) that fails if the
constraint admits any 2.x version, or if the installed SDK lacks the decorators
`build_server` uses,

**and neglected** (1) porting `iris_mcp` to the SDK 2.x API now — rejected as the
production fix: it touches every handler registration plus the HTTP/session-manager
wiring and needs its own design and test pass, while the service is down; it is
the intended follow-up and will supersede this cap; (2) pinning an exact version
(`mcp==1.30.0`) — rejected: it blocks 1.x security/bug-fix releases for no benefit,
since the break is a major-version API removal; (3) introducing a lockfile for the
Docker build — deferred: a larger build change than an outage fix warrants, and
Protocol §11 (latest stable) still needs a deliberate upgrade path rather than a
frozen tree,

**to achieve** a bootable `iris-mcp` on the next deploy and a CI/dev-time signal
before an unbounded major bump can reach production again,

**accepting that** iris-mcp stays on SDK 1.x (a deliberate, documented exception to
Protocol §11) until the 2.x port lands.

---

## Consequences

- **Deploy config / dependency only.** No schema, endpoint, MCP tool, or CLI change;
  surface parity (§14) and migration parity (§15) are N/A.
- The stdio install path (`uvx --from git+…#subdirectory=mcp`) gets the same cap.
- Follow-up: port `iris_mcp` to MCP SDK 2.x and lift the cap (new ADR superseding
  this one).

## Dependencies

- ADR-134 (standalone iris-mcp service and its Dockerfile).

## References

- Implementation spec: [SPEC-244-A](./specs/SPEC-244-A-Cap-MCP-SDK-Below-v2.md)
