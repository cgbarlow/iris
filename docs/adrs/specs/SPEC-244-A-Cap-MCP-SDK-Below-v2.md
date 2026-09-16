# SPEC-244-A: Cap the MCP Python SDK below 2.x

Implements **[ADR-244](../ADR-244-Cap-MCP-SDK-Below-v2.md)**.

## 1. Dependency

`mcp/pyproject.toml` → `[project].dependencies`:

| Before | After |
|--------|-------|
| `"mcp>=1.2"` | `"mcp>=1.2,<2"` |

Resolves to `mcp` 1.30.0 as of 2026-09-16. No other package in the repo depends on
`mcp` directly.

## 2. Failure being fixed

Render `iris-mcp` deploy of v6.48.0 installed `mcp-2.2.0`, then at boot:

```
File ".../iris_mcp/server.py", line 53, in build_server
    @server.list_tools()
AttributeError: 'Server' object has no attribute 'list_tools'
```

## 3. Tests (TDD)

`mcp/tests/test_sdk_version_pin.py` (red before the change, green after):

1. `test_mcp_dependency_excludes_sdk_v2` — the parsed `mcp` specifier does not
   contain `2.0.0` or `2.2.0`.
2. `test_mcp_dependency_still_allows_v1` — it still contains `1.2.0`.
3. `test_installed_sdk_exposes_low_level_decorators` — `mcp.server.lowlevel.Server`
   has callable `list_tools`, `call_tool`, `list_resources`, `read_resource`,
   `list_prompts`, `get_prompt`.

## 4. Verification

- Reproduced: `docker build -f mcp/Dockerfile .` on `main` → `mcp` 2.2.0 → same
  `AttributeError` on `uvicorn iris_mcp.http_main:create_app --factory`.
- Fixed: same build with the cap → `mcp` 1.30.0 → "Application startup complete";
  `GET /` answers (401, auth-gated as expected).

## 5. Out of scope

- Porting `iris_mcp` to the SDK 2.x API (follow-up ADR supersedes this cap).
