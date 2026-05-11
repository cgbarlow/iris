# SPEC-152-A: MCP `prompts` capability for scope system prompts

ADR: [ADR-152](../ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md)

## Backend

### `GET /api/prompts/scope-index`

| | |
|---|---|
| Auth | Anonymous-readable (matches `/api/collections`, `/api/sets`). |
| Response | `200 OK` + `ScopePromptIndexResponse`. |
| Errors | None — empty list when no scopes have a system_prompt. |

```python
class ScopePromptIndexEntry(BaseModel):
    name: str                                    # "set:<uuid>" | "collection:<uuid>"
    scope_type: Literal["collection", "set"]
    scope_id: str
    scope_name: str
    description: str | None = None
    body: str                                    # the system_prompt body, trimmed

class ScopePromptIndexResponse(BaseModel):
    items: list[ScopePromptIndexEntry]
```

### Service: `app/prompts/service.py:list_scope_prompts(db)`

Two SELECTs:

```sql
SELECT id, name, description, system_prompt FROM collections
WHERE is_deleted = 0 AND system_prompt IS NOT NULL
ORDER BY name;

SELECT id, name, description, system_prompt FROM sets
WHERE is_deleted = 0 AND system_prompt IS NOT NULL
ORDER BY name;
```

Whitespace-only `system_prompt` values are filtered out in Python
(`body.strip()` before append). Collections always come first, then
Sets. Within each group, alphabetical by name.

### Registration

`backend/app/main.py` — single `app.include_router(prompts_router)`
call alongside `collections_router` / `sets_router`.

## iris-client

### `IrisClient.list_scope_prompts() -> list[ScopePromptIndexEntry]`

Thin wrapper over `GET /api/prompts/scope-index`. Tolerates both
`{"items": [...]}` and bare `[...]` response shapes for forward
compatibility. New model `ScopePromptIndexEntry` lives in
`iris-client/src/iris_client/models/core.py` with the `_Permissive`
base.

## MCP server

### Module: `mcp/src/iris_mcp/prompts.py`

```python
_NAME_RE = re.compile(r"^(set|collection):([0-9a-f-]{36})$")

async def list_prompts(client: IrisClient) -> list[types.Prompt]: ...
async def get_prompt(client: IrisClient, name: str, arguments: dict[str, str] | None = None) -> types.GetPromptResult: ...
```

#### `list_prompts`
Calls `client.list_scope_prompts()`, maps each entry to:

```python
types.Prompt(
    name=entry.name,
    description=_short_description(entry.scope_type, entry.scope_name, entry.description),
    arguments=[],
)
```

`_short_description` formats as `"{Scope}: {name} — {description}"`
(or `"{Scope}: {name}"` if description is empty), truncated at 200
characters with a trailing `...`.

#### `get_prompt`
1. Match `name` against `_NAME_RE`; raise `ValueError("Invalid Iris
   scope-prompt name: ...")` on miss.
2. Re-call `client.list_scope_prompts()`; find the entry with matching
   `name`; raise `ValueError("... not found")` on miss.
3. Build `preamble + body` where preamble is `'Loaded from Iris
   {Scope} "<name>" (<web_url>):\n\n'` if `IRIS_WEB_URL` set, else
   `'Loaded from Iris {Scope} "<name>":\n\n'`.
4. Return:
   ```python
   types.GetPromptResult(
       description=_short_description(...),
       messages=[
           types.PromptMessage(
               role="user",
               content=types.TextContent(type="text", text=preamble + body),
           ),
       ],
   )
   ```

### Registration in `mcp/src/iris_mcp/server.py`

```python
@server.list_prompts()
async def _list_prompts() -> list[types.Prompt]:
    return await iris_prompts.list_prompts(client)

@server.get_prompt()
async def _get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    return await iris_prompts.get_prompt(client, name, arguments)
```

The MCP SDK auto-advertises the `prompts` capability once these
decorators are registered — no explicit capability declaration needed
at `Server(...)` instantiation. The same pattern already works for
`list_tools` and `list_resources`.

## Tests

| File | Cases | Layer |
|---|---|---|
| `backend/tests/test_prompts/test_router.py` | 6 (empty index; set; collection-before-sets; null system_prompt excluded; whitespace excluded; anonymous-readable) | backend |
| `iris-client/tests/test_scope_prompts.py` | 2 (typed entries; empty index) | iris-client |
| `mcp/tests/test_prompts_list.py` | 5 (empty; set; collection; description truncation; order) | MCP |
| `mcp/tests/test_prompts_get.py` | 7 (set happy path; collection happy path; web URL present when env set; web URL absent when env unset; malformed name; wrong scope type; unknown UUID) | MCP |

Total: 20 new tests.

## End-to-end verification

1. Author a system_prompt on a Set via `/sets/<id>`.
2. Configure Claude Desktop with the UAT Iris MCP server; restart it.
3. Open the prompt picker → confirm `set:<uuid>` appears with
   "Set: <name> — <description>" visible.
4. Invoke it → confirm the conversation seeds with the preamble +
   body as a user message. The model treats it as authoritative.
5. Send a follow-up question; confirm Claude's response reflects the
   loaded directive (e.g., cites tools, follows style rules).
6. Delete the system_prompt on `/sets/<id>` → confirm the prompt
   disappears from the picker on the next `prompts/list` call.
7. Iris MCP `ask` against the same set still applies the prompt
   server-side (no regression vs v5.8.0).

## Out of scope (deferred per ADR-152)

- Argument templating.
- Multiple prompts per scope.
- Visibility filtering by user / role.
- Prompt search / fuzzy match.
