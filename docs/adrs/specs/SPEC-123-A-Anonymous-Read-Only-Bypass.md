# SPEC-123-A: Anonymous Read-Only Bypass

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-123-A |
| **ADR** | [ADR-123](../ADR-123-Anonymous-Read-Only-Bypass.md) |
| **Status** | Approved |
| **Date** | 2026-04-21 |

## Overview

Anonymous visitors can read Iris content, use search, view the
knowledge graph, and use Ask AI (rate-limited per-IP). Writes and admin
views still require authentication.

## Backend

### New dependency

```python
# backend/app/auth/dependencies.py

async def get_optional_user(request: Request) -> dict[str, Any] | None:
    """Return the authenticated user if a valid token is present.

    Returns None when no Authorization header is sent — the caller is
    treated as anonymous. Raises 401 when the header is present but the
    token is invalid (anonymous ≠ "valid user with no claims" — a bad
    token is still a client error).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    # Delegate to get_current_user for Bearer-prefix check + validation.
    return await get_current_user(request)
```

### Routers switched to optional auth

One-line change per route: `Depends(get_current_user)` →
`Depends(get_optional_user)`.

| Router | GET endpoints switched |
|---|---|
| `collections/router.py` | list, get, list-packages, list-sets, list-diagrams, list-elements |
| `sets/router.py` | list, get, list-packages, list-diagrams, list-elements |
| `packages/router.py` | list, get, list-children, get-hierarchy, relationships |
| `diagrams/router.py` | list, get, get-canvas |
| `elements/router.py` | list, get, list-relationships |
| `graph/router.py` | get-graph, get-settings |
| `search/router.py` | search |
| `bookmarks/router.py` | list (reads only — writes stay mandatory) |
| `ai/router.py` | providers-active, discuss (see rate-limit note below) |

Write endpoints (POST/PUT/PATCH/DELETE) and admin routers (`users`,
`audit`, `locks`, `settings`, `admin/*`, `import`, `recycle-bin/*`
writes) are unchanged — they still use `get_current_user` or
`require_permission(...)`.

Each router's `get_optional_user`-backed handler passes the user or
`None` through to its service call; services filter responses as if
the caller had `role='viewer'` when user is `None` (i.e. apply the
most restrictive read policy). Current services don't filter by role
— they return everything a valid user can see — so `None` threads
through unchanged for v4.1 deployments where all data is public.

### Rate-limit category `anon_ai`

Extend `backend/app/middleware/rate_limit.py`:

```python
def _get_rate_category(request: Request) -> str:
    path = request.url.path
    if path == "/api/auth/login":
        return "login"
    if path == "/api/auth/refresh":
        return "refresh"
    if path.startswith("/api/ai/") and not request.headers.get("Authorization"):
        return "anon_ai"
    return "general"
```

Middleware limits dict gains `anon_ai: kwargs.get("anon_ai", 10)`.
Window for `anon_ai` is 3600 s (1 hour) — pass an optional `window`
param down from `is_allowed(..., window=3600)` for this category.
Other categories keep the 60 s window.

Config:

```python
# backend/app/config.py
anon_ai_rate_limit: int = field(
    default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_ANON_AI", "10")),
)
```

Wire the new field into middleware registration in `main.py`.

## Frontend

### Auth store

```ts
// frontend/src/lib/stores/auth.svelte.ts
export function isAnonymous(): boolean {
  return !isAuthenticated();
}
```

### Root layout

```svelte
<!-- frontend/src/routes/+layout.svelte -->
<script lang="ts">
  // …
  const publicRoutes = ['/login'];
  const isPublicRoute = $derived(publicRoutes.includes(page.url.pathname));
  // NOTE: Auth redirect removed. Anonymous users may reach any non-admin
  // route. Admin routes gate themselves in their own +layout.
</script>

{#if isPublicRoute}
  {@render children()}
{:else}
  <AppShell>
    {@render children()}
  </AppShell>
  {#if !isAnonymous()}
    <SessionTimeoutWarning />
  {/if}
{/if}
```

### Admin layout gate

New `frontend/src/routes/admin/+layout.svelte` (wraps all `/admin/*`
routes) that redirects to `/login` when anonymous:

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';
  import { isAuthenticated } from '$lib/stores/auth.svelte.js';
  import { onMount } from 'svelte';
  let { children } = $props();
  onMount(() => {
    if (!isAuthenticated()) goto('/login');
  });
</script>
{#if isAuthenticated()}
  {@render children()}
{/if}
```

### AppShell menu variants

`AppShell.svelte` reads `isAnonymous()` and:

- Shows a "Sign in" button in place of the Sign-out button.
- Hides the Admin submenu (Users, Audit, Locks, Admin Settings).
- Hides the Import and Recycle Bin items (both write-oriented).
- Hides the Settings gear (per-user settings).
- Keeps Dashboard, Collections, Sets, Diagrams, Elements, Bookmarks,
  Guide, Help, Ask AI.

### Per-page write UI hiding

Pages that expose write buttons add:

```ts
import { isAuthenticated } from '$lib/stores/auth.svelte.js';
const canWrite = $derived(isAuthenticated());
```

Affected pages (write UI wrapped in `{#if canWrite}`):

- `routes/collections/+page.svelte` — "New Collection" button
- `routes/sets/+page.svelte` — "New Set" button, batch actions
- `routes/sets/[id]/+page.svelte` — "Edit", "Delete", "Import",
  add-package/diagram/element
- `routes/packages/[id]/+page.svelte` — create child, edit, delete,
  move
- `routes/diagrams/[id]/+page.svelte` — canvas edit affordances
  (drag-to-rearrange, add element, save), lock UI
- `routes/elements/[id]/+page.svelte` — edit, delete, add
  relationship
- `routes/bookmarks/+page.svelte` — no write UI visible today; no
  change
- `routes/ask/+page.svelte` — "Send" button remains visible
  (anonymous AI allowed); no changes.

## Tests

### Backend

`backend/tests/test_auth/test_optional_auth.py`:

- `GET /api/collections` with no Authorization → 200.
- `POST /api/collections` with no Authorization → 401.
- `GET /api/admin/users` with no Authorization → 401.
- `GET /api/collections` with invalid token → 401 (not 200).

`backend/tests/test_middleware/test_anon_rate_limit.py`:

- 10 anonymous `POST /api/ai/discuss` requests → all ≠ 429.
- 11th anonymous request → 429.
- Authenticated AI requests continue to use `general` bucket (no
  interference).

### Frontend

`frontend/tests/e2e/anonymous-readonly.spec.ts`:

- Clear localStorage + sessionStorage, navigate to `/`.
- Assert dashboard heading visible (no redirect to `/login`).
- Assert no "New Collection" / "New Set" buttons.
- Assert "Sign in" button in AppShell.
- Navigate to `/admin/users` → expect redirect to `/login`.
- Log in as admin, re-visit `/` — assert write buttons now visible.

## Acceptance criteria

1. Anonymous GET on public read endpoints returns 200 with data.
2. Anonymous POST/PUT/PATCH/DELETE on any endpoint returns 401.
3. Anonymous 11th AI request within an hour returns 429.
4. Anonymous `/admin/users` redirects to `/login` in frontend.
5. Invalid-token requests still return 401 (not silently anonymous).
6. Existing authenticated flows (login, all write operations, admin
   pages) unchanged.

## Out of scope

- Private-data deployment flag to disable anonymous reads. Deferred;
  UAT intent is fully public.
- Per-entity sharing or "this collection is public / that one is
  private" visibility rules. Deferred.
- CDN caching of anonymous responses.
- A formal "anonymous" role in the roles table.
