# SPEC-161-A: MCP entity-creation tools + destination-confirmation flow

ADR: [ADR-161](../ADR-161-MCP-Entity-Creation-and-Destination-Flow.md)

## Database

**No schema changes.** All three target endpoints (`POST /api/collections`, `POST /api/sets`, `POST /api/packages`) already exist with their Pydantic request models (`CollectionCreate`, `SetCreate`, `PackageCreate`).

## Backend

**No changes.** The endpoints already gate on `get_current_user` (`backend/app/auth/dependencies.py`). v5.15.0's pairing-issued PATs satisfy this dependency without modification.

## iris-client

Three new methods on `IrisClient` (`iris-client/src/iris_client/client.py`):

```python
async def create_collection(
    self, name: str, *, description: str | None = None,
) -> Collection:
    """POST /api/collections. Auth required."""

async def create_set(
    self,
    name: str,
    *,
    collection_id: str | None = None,
    description: str | None = None,
) -> IrisSet:
    """POST /api/sets. Auth required."""

async def create_package(
    self,
    name: str,
    *,
    set_id: str | None = None,
    parent_package_id: str | None = None,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Package:
    """POST /api/packages. Auth required."""
```

Reuses the existing permissive response models `Collection`, `IrisSet`, `Package` from `iris-client/src/iris_client/models/core.py`. No new models.

## MCP server

### Three new tools

In `mcp/src/iris_mcp/tools.py`:

| Tool name | Required arg | Optional args | Wraps |
|---|---|---|---|
| `create_collection` | `name` | `description` | `client.create_collection` |
| `create_set` | `name` | `collection_id`, `description` | `client.create_set` |
| `create_package` | `name` | `set_id`, `parent_package_id`, `description`, `metadata` | `client.create_package` |

Each handler:
- Calls the matching iris-client method.
- On `IrisAuthError`, returns `_auth_required_payload(action)` (shared helper extracted from the existing `_save_doview_analysis` 401 branch).
- On success, returns the new entity's `.model_dump_json()`.

### Shared `_auth_required_payload` helper

Extract from `_save_doview_analysis`'s existing 401 branch:

```python
def _auth_required_payload(action: str) -> str:
    """v5.15.0 / ADR-160 pairing-recovery payload. Used by every
    write tool's 401 branch so the recovery instructions are
    identical across tools."""
    return json.dumps({
        "success": False,
        "error": "auth_required",
        "message": (
            f"{action} failed — this MCP connection isn't authenticated"
            f" yet.\n\nTo fix:\n  1. Visit {_pairing_url()}\n"
            "  2. Click 'Generate pairing code'\n"
            "  3. Paste the code back here, and I'll call iris_authenticate.\n\n"
            "(After that, this MCP connection stays authenticated"
            " for ~90 days on this machine.)"
        ),
        "pairing_url": _pairing_url(),
        "next_tool": "iris_authenticate",
    })
```

Update `_save_doview_analysis`'s 401 branch to call this helper. New create_* handlers use it directly.

### Destination-confirmation preamble

Constant in `mcp/src/iris_mcp/tools.py`:

```python
_DESTINATION_PREAMBLE = """
BEFORE CALLING, confirm with the user where they want this saved.

Options to offer the user (use AskUserQuestion when the client
supports it; otherwise a numbered list):

  1. An existing set (or set + parent package) the user names.
     Use list_collections / list_sets / package_hierarchy to
     resolve human names to ids.
  2. A new set in an existing collection.
     Call create_set(name=..., collection_id=<existing>) first,
     then save against the returned set.id.
  3. A new collection and a new set.
     Call create_collection(name=...) then
     create_set(name=..., collection_id=<new>), then save.
  4. (Optional) Also nest under a new package.
     Call create_package(name=..., set_id=<chosen>) and pass its
     id as parent_package_id.

Only call this save tool once the user has chosen / confirmed a
destination. Do not pick a destination silently.
""".strip()
```

The preamble is injected into the descriptions of:
- `save_doview_analysis` (existing; description gets the preamble appended).
- `create_collection`, `create_set`, `create_package` (new; descriptions reference the preamble as the calling context, plus their own operational details).

### Tool descriptions (new tools)

- `create_collection`: "Create a new top-level Collection in Iris (ADR-161, v5.16.0). Use after the user has confirmed they want a new collection — see destination-confirmation guidance below. Returns the new collection's id and metadata; pass the id to `create_set(collection_id=…)` to nest a set inside it. Auth required (the v5.15.0 pairing flow covers this)."
- `create_set`: "Create a new Set in Iris (ADR-161, v5.16.0). Pass collection_id=… to nest under an existing collection, or omit for a top-level (uncollected) set. Use after the user has confirmed they want a new set — see destination-confirmation guidance below. Returns the new set's id; pass it as save_doview_analysis(set_id=…) or create_package(set_id=…). Auth required."
- `create_package`: "Create a new Package in Iris (ADR-161, v5.16.0). A package is a folder inside a set; use this to organise multiple diagrams under a shared parent. Pass set_id=<chosen set> and parent_package_id=<parent> to nest, or omit parent_package_id for a root-level package. Use after the user has confirmed they want a new package — see destination-confirmation guidance below. Auth required."

The preamble (`_DESTINATION_PREAMBLE`) is concatenated to each of the above plus `save_doview_analysis`.

## Frontend

### Default Notation dropdown fix

`frontend/src/routes/settings/+page.svelte` — extend the existing `<select id="settings-notation">` block with three options after `c4`:

```svelte
<option value="doview">DoView — outcomes-based theory of change</option>
<option value="markdown">Markdown — text content with embedded mermaid</option>
<option value="bpmn">BPMN — business process model and notation (preview)</option>
```

Values verified against migrations m027 (`doview`), m043 (`bpmn`), m051 (`markdown`). No store changes.

## Tests

| File | Cases | Layer |
|---|---|---|
| `iris-client/tests/test_create_endpoints.py` | 6 — create_collection happy; create_set with/without collection_id; create_package with optional parent + metadata; IrisAuthError mapping on 401; permissive-model extra-fields | iris-client |
| `mcp/tests/test_tools_create.py` | 10 — three happy paths; three auth_required payloads (assert structure: success=False, error="auth_required", pairing_url, next_tool="iris_authenticate"); preamble appears in save_doview_analysis.description; preamble appears in each create_ tool's description; the new tools appear in `tool_definitions()` with non-empty `inputSchema.properties` | mcp |
| `frontend/tests/unit/settingsNotationDropdown.test.ts` | 1 — all 7 notation IDs (simple, uml, archimate, c4, doview, markdown, bpmn) appear as option values | frontend |

**Total**: 17 new tests for v5.16.0.

## End-to-end verification

After UAT deploy:

1. In Claude Desktop with v5.15.0 pairing token persisted, ask: "save the analysis under a new collection called 'My Outcomes Work' and a new set called 'Pilot DoView'."
2. Confirm Claude offers the four-option destination menu (AskUserQuestion or numbered list).
3. Pick "new collection + new set" — confirm Claude calls `create_collection`, then `create_set(collection_id=<new>)`, then `save_doview_analysis(set_id=<new>, …)`.
4. Browse `/collections` — confirm the new collection + set exist and the diagram is inside.
5. Repeat with "new set under existing collection" — only `create_set` called.
6. Repeat with "new package under existing set" — only `create_package` called.
7. Revoke the active PAT in Iris; re-run any create_ flow — every tool should return the same `auth_required` payload pointing at `/settings/mcp-pairing`.
8. Open `/settings` — confirm Default Notation dropdown lists all 7 notations.

## Out of scope (deferred)

- Element / relationship MCP write tools.
- Bulk container creation in one call.
- Server-side find-or-create idempotency for the create endpoints.
- Container delete / rename MCP tools.
