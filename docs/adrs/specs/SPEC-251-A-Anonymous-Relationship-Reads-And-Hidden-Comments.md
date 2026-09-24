# SPEC-251-A: Anonymous Relationship Reads, and No Comments UI for Anonymous Visitors

Implements **[ADR-251](../ADR-251-Anonymous-Relationship-Reads-And-Hidden-Comments.md)**.
Amends [SPEC-249-A](./SPEC-249-A-Relationship-Tools-For-Agents.md) (relationship read auth).

## 1. Changes

| File | Change |
|------|--------|
| `backend/app/relationships/router.py` | `GET /api/relationships` and `GET /api/relationships/{id}` depend on `get_optional_user`. Writes unchanged (`get_current_user`). |
| `backend/app/seed/creation_prompts.py`, `mcp/src/iris_mcp/server_instructions.py` | AUTH RECOVERY back to "Read tools (search, get_*, list_*, package_hierarchy) work without sign-in; only writes (create_*, update_*, delete_*) need it." |
| `mcp/src/iris_mcp/tools.py` | `list_relationships` / `get_relationship` descriptions no longer claim sign-in is needed. |
| `mcp/README.md`, `docs/api.md` | Relationship reads documented as anonymous-friendly. |
| `frontend/src/lib/components/CommentsPanel.svelte` | `writable = !isAnonymous() && canWrite(collectionId)` (panel hidden when anonymous); comments fetched only when signed in. |
| `frontend/src/routes/views/[id]/+page.svelte` | `commentsAvailable = $derived(!isAnonymous())`; all four Comments toggles gated on it; `loadCommentCount` returns early (count 0) when anonymous. |

The element page needs no change: its only comments UI is `CommentsPanel`.

## 2. Tests (TDD)

Backend, `tests/test_relationships/test_agent_relationship_surface.py`:
- New `TestAnonymousReads`:
  - anonymous list by `element_id`, and by `set_id` plus `relationship_type`, returns 200 with roles and `data`;
  - anonymous `GET /api/relationships/{id}` returns 200;
  - a bad bearer token still gets 401 on both reads;
  - `PUT` and `DELETE` without sign-in still get 401.
- `test_server_instructions_seed_points_at_relationship_tools` now asserts the carve-out is gone.
- Red before the router and seed change (4 failures), green after (46 passed in `tests/test_relationships`).

MCP, `mcp/tests/test_relationship_tools.py`: the two ADR-249 sign-in assertions are inverted. The fallback instructions have no carve-out, and the tool descriptions don't mention sign-in. The rest of the suite passes, apart from 2 inventory tests that fail on main too.

Frontend:
- `tests/unit/anonymousCommentsHidden.test.ts` (source contract, same style as `canvasTabFirst.test.ts`). It checks that the panel is gated and doesn't fetch when anonymous, that every Comments toggle is gated, and that the count request is skipped. 6 tests: red before, green after.
- `tests/e2e/anonymous-readonly.spec.ts`: new "anonymous visitor sees no comments UI on a diagram". Anonymously, a diagram page has no Comments button, no "Failed to load comments" text and no `/comments` request. After signing in, the Comments button is back. Before the change it failed (a Comments button was present); after the change it passes, along with the other 4 tests in the spec.

## 3. Acceptance criteria

- Anonymous callers can list and read relationships; writes still need sign-in.
- Anonymous visitors see no comments UI and trigger no comments request; signed-in users are unaffected.
