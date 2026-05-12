# SPEC-162-A: Generic MCP diagram-creation workflow

ADR: [ADR-162](../ADR-162-Generic-MCP-Diagram-Creation-Workflow.md)

## Database

**No schema changes.**

## Backend

### `backend/app/ai/router.py:872-944`

Both endpoints gain a `purpose: str = Query("response_format")` parameter, validated against `{"response_format", "creation_format"}`. Invalid values return 422.

```python
@router.get("/response-prompts/types")
async def list_response_format_types(
    request: Request,
    purpose: str = Query("response_format", description="..."),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),
) -> list[ResponseFormatType]:
    if purpose not in ("response_format", "creation_format"):
        raise HTTPException(status_code=422, detail="...")
    # Existing SQL but with WHERE p.purpose = :purpose parameterised.
```

```python
@router.get("/response-prompts/composed")
async def get_response_prompt_composed(
    request: Request,
    notation: str = Query(...),
    diagram_type: str | None = Query(default=None),
    purpose: str = Query("response_format"),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),
) -> ResponsePromptComposed:
    if purpose == "creation_format":
        body = await build_creation_system_prompt(db, notation, diagram_type)
    elif purpose == "response_format":
        body = await build_response_system_prompt(db, notation, diagram_type)
    else:
        raise HTTPException(status_code=422, detail="...")
    return ResponsePromptComposed(body=body, ...)
```

Both `build_response_system_prompt` and `build_creation_system_prompt` are already purpose-aware (`backend/app/ai/creation.py`).

### Backend tests (`backend/tests/test_ai/...`)

- Default `?purpose=response_format` behaviour unchanged on both endpoints.
- `?purpose=creation_format` returns creation cascade on `/composed`.
- `?purpose=creation_format` returns creation-format pairs on `/types`.
- `?purpose=garbage` returns 422 on both endpoints.

## iris-client

### Methods (`iris-client/src/iris_client/client.py`)

```python
async def list_response_format_types(
    self, *, purpose: str = "response_format",
) -> list[ResponseFormatType]:
    response = await self._request(
        "GET", "/api/ai/response-prompts/types",
        params={"purpose": purpose},
    )
    ...

async def get_response_prompt(
    self,
    notation: str,
    *,
    diagram_type: str | None = None,
    purpose: str = "response_format",
) -> ResponsePromptComposed:
    params: dict[str, Any] = {"notation": notation, "purpose": purpose}
    if diagram_type is not None:
        params["diagram_type"] = diagram_type
    response = await self._request(
        "GET", "/api/ai/response-prompts/composed", params=params,
    )
    ...
```

### Tests (`iris-client/tests/test_creation_prompts.py`)

- `purpose='creation_format'` flows through to the request.
- `purpose='response_format'` is the default (no params provided → same query).
- Both happy-path return-shape assertions.
- Tolerates extra fields on response (permissive model).

## MCP server

### New shared constant (`mcp/src/iris_mcp/tools.py`)

```python
_CREATION_FLOW_PREAMBLE = """
Generic save for a new diagram of any (notation, diagram_type) pair.

CREATION FLOW (recommended):
  1. Discover: call list_notations / list_diagram_types if you don't
     already know which (notation, diagram_type) the user wants.
  2. Fetch the creation guidance: get_response_prompt(notation=...,
     diagram_type=..., purpose='creation_format'). The body carries the
     layered creation cascade (base + notation + diagram_type) used by
     Iris AI when generating diagrams. For DoView it includes the
     5-question guided conversation, the entity types, the colour
     palette, and the outcomes_map layout rules.
  3. Run the guided conversation IN CHAT with the user. Use
     AskUserQuestion when supported; numbered list otherwise.
  4. Compose the `data` JSON locally per the creation prompt's rules.
     For visual diagrams (notation in doview / archimate / c4 / uml /
     simple / bpmn), data is a Svelte-Flow-shaped {nodes, edges}
     payload. For markdown diagrams, data is {"content": "<markdown>"}.
  5. Confirm destination with the user (see destination preamble below).
  6. Call create_diagram with the composed data.
""".strip()
```

### New tools

| Tool | Required args | Optional args |
|---|---|---|
| `create_diagram` | `set_id`, `name`, `notation`, `diagram_type` | `data` (object), `parent_package_id`, `description` |
| `list_notations` | — | — |
| `list_diagram_types` | — | — |

`create_diagram` description = `_CREATION_FLOW_PREAMBLE` + `\n\n` + `_DESTINATION_PREAMBLE`. On `IrisAuthError` → `_auth_required_payload("Create diagram")` (v5.16.0 shared helper).

`list_notations` / `list_diagram_types` wrap the existing `/api/registry/notations` and `/api/registry/diagram-types` endpoints respectively.

### Extended tools

`get_response_prompt` and `list_response_format_types` tool definitions gain an optional `purpose` arg in their input schema:

```python
"purpose": (
    {
        "type": "string",
        "enum": ["response_format", "creation_format"],
        "default": "response_format",
        "description": (
            "Which prompt cascade to fetch. 'response_format' (default) "
            "for output-shape rules; 'creation_format' for the "
            "drafting/composition rules Iris AI uses when generating a "
            "diagram. Pair with create_diagram for local-AI-driven "
            "diagram creation."
        ),
    },
    False,
),
```

Handler passes the arg through to the iris-client method.

### `save_doview_analysis` deprecation

Description rewritten to prefix:

```text
[Deprecated since v5.17.0 (ADR-162): prefer create_diagram(
notation='markdown', diagram_type='doview_analysis', set_id=...,
name=..., data={'content': '<markdown>'}, parent_package_id?). Will be
removed in v6.0.0.]

[then existing description body unchanged]
```

Handler body unchanged. Behaviour unchanged.

### Regression test (`mcp/tests/test_tools_authenticate.py`)

New test `test_pairing_then_create_set_uses_new_pat_in_same_session`:

- Mock pairing exchange returns `iris_pat_freshly_minted`.
- Mock `POST /api/sets`: return 201 iff `Authorization == 'Bearer iris_pat_freshly_minted'`, else 401.
- Long-lived `c = IrisClient(token=None)`.
- `await tools.dispatch("iris_authenticate", c, {"credential": "IRIS-..."})` — succeeds.
- `await tools.dispatch("create_set", c, {"name": "X"})` — must succeed; `"auth_required"` must NOT appear in the result body.

Catches any regression that would re-introduce the v5.15.0 symptom (user reported `iris_authenticate` succeeded but next call still got `auth_required`).

### MCP tests

- `mcp/tests/test_tools_create_diagram.py`:
  - `create_diagram` happy paths for `doview/outcomes_map`, `markdown/doview_analysis`, `simple/component`.
  - 401 → `auth_required` payload.
  - Description carries both preambles.
- `mcp/tests/test_tools_list_notations_and_diagram_types.py`:
  - `list_notations` returns all registered notations in display_order.
  - `list_diagram_types` returns diagram_types with their compatible `notations` arrays.

## Frontend

### Fix #1 — sessionStorage fallback (`frontend/src/lib/stores/auth.svelte.ts`)

```ts
function loadFromSession(): StoredAuth | null {
    if (typeof sessionStorage === 'undefined') return null;
    try {
        let raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw && typeof localStorage !== 'undefined') {
            raw = localStorage.getItem(STORAGE_KEY);
            if (raw) sessionStorage.setItem(STORAGE_KEY, raw);
        }
        if (!raw) return null;
        return JSON.parse(raw) as StoredAuth;
    } catch {
        return null;
    }
}
```

### Fix #2 — login redirect-back (`frontend/src/routes/login/+page.svelte`)

```ts
import { page } from '$app/state';

function safeRedirect(): string {
    const r = page.url.searchParams.get('redirect');
    if (!r) return '/';
    // Same-origin path only: must start with /, must NOT start with //,
    // must NOT contain ://, must NOT contain whitespace.
    if (!r.startsWith('/')) return '/';
    if (r.startsWith('//')) return '/';
    if (r.includes('://')) return '/';
    if (/\s/.test(r)) return '/';
    return r;
}

// Replace each goto('/') with goto(safeRedirect())
```

`/settings/mcp-pairing` and `/settings` sign-in hints update to point at `/login?redirect=<encoded-current-path>`.

### Fix #3 — cascading filter dropdowns (`frontend/src/routes/admin/settings/ai/+page.svelte`)

Extract helpers:

```ts
function compatibleDiagramTypes(
    notationId: string | null,
    allDts: DiagramTypeRegistry[],
): DiagramTypeRegistry[] {
    if (!notationId) return allDts;
    return allDts.filter(dt =>
        dt.notations.some(n => n.notation_id === notationId),
    );
}

function compatibleNotations(
    dtId: string | null,
    allDts: DiagramTypeRegistry[],
    allNotations: NotationRegistry[],
): NotationRegistry[] {
    if (!dtId) return allNotations;
    const dt = allDts.find(d => d.id === dtId);
    if (!dt) return allNotations;
    const validIds = new Set(dt.notations.map(n => n.notation_id));
    return allNotations.filter(n => validIds.has(n.id));
}
```

Apply at three call sites (filter row, create dialog, edit dialog). When `layer === 'base'` in any of those sites, disable both pickers and surface the hint "base layer applies universally (no notation / diagram_type)".

### Fix #4 — inclusion logic (same file)

```ts
function isNotationScopeMatch(
    p: { notation: string | null; diagram_type: string | null },
    notationFilter: string,
    allDts: DiagramTypeRegistry[],
): boolean {
    if (!notationFilter) return true;
    if ((p.notation ?? '') === notationFilter) return true;
    if (!p.diagram_type) return false;
    const dt = allDts.find(d => d.id === p.diagram_type);
    return !!dt?.notations.some(n => n.notation_id === notationFilter);
}
```

`filteredPrompts` uses this in place of the exact-match notation check. `diagramTypeFilter` stays exact-match.

### Frontend tests

| File | Cases |
|---|---|
| `frontend/tests/unit/authStoreLocalStorageFallback.test.ts` | 4 — sessionStorage hit (unchanged); sessionStorage empty + localStorage seeded → loaded AND copied back to session; both empty → null; corrupt JSON → null |
| `frontend/tests/unit/loginRedirectBack.test.ts` | 5 — `?redirect=/x` honoured; missing param → /; `//evil` rejected; `http://evil` rejected; whitespace rejected |
| `frontend/tests/unit/adminPromptFilterCascade.test.ts` | 4 — compatibleDiagramTypes filters by notations array; compatibleNotations does the reverse; empty notationFilter passes through; both filters consistent across registry shapes |
| `frontend/tests/unit/adminPromptFilterInclusion.test.ts` | 4 — direct notation match; indirect via diagram_type_notations; base-layer rows excluded from notation filter; unrelated-notation rows excluded |

## Documentation

### `docs/prompts/doview-book-mcp-system-context.md`

Trim. Remove the entire path-A / path-B step-by-step. Replace with the lean orient content described in the plan — chapter overview, four-option menu, single sentence routing diagram-creation requests at `create_diagram` (the tool's description carries the workflow).

### `README.md`

- "Exposes ~22 tools" → "Exposes ~26 tools" with `create_diagram`, `list_notations`, `list_diagram_types` mentioned.
- Brief one-line note that `save_doview_analysis` is deprecated in v5.17.0, removal in v6.0.0.

### `CHANGELOG.md`

`[5.17.0]` block covers:
- Generic `create_diagram` MCP tool + `list_notations` + `list_diagram_types` discoverability.
- `get_response_prompt` / `list_response_format_types` extended with `purpose` (back-compat default).
- Backend `/api/ai/response-prompts/{types,composed}` extended with `?purpose=` (back-compat default).
- iris-client method extensions.
- `save_doview_analysis` deprecated.
- Frontend fixes: cross-tab auth, login redirect-back, admin filter cascading dropdowns, admin filter inclusion logic.
- `mcp_system_context` for Outcomes Theory Book set trimmed.
- v5.15.0-symptom regression test added.

## End-to-end verification

Listed in the plan file. Key flows:

1. New tab opened from Claude's pairing-page link inherits auth state.
2. Sign in from `/settings/mcp-pairing` returns to that page, not dashboard.
3. Claude Desktop end-to-end: ask for a new DoView outcomes map → Claude fetches `get_response_prompt(notation='doview', diagram_type='outcomes_map', purpose='creation_format')` → runs the 5-question conversation → confirms destination → calls `create_diagram` → saved diagram appears in Iris.
4. `/admin/settings/ai` filter dropdowns cascade; selecting `doview` shows all doview-relevant rows (direct + diagram_type-mapped).
5. v5.15.0 symptom — no longer reproducible; regression test covers it.

## Out of scope (deferred)

- Removal of `save_doview_analysis` (v6.0.0).
- Rename of `get_response_prompt` to `get_diagram_prompt` (v6.0.0).
- JSON-Schema data-shape endpoint.
- `create_element` / `create_relationship` MCP tools.
- DoView balance-check validator tool.
