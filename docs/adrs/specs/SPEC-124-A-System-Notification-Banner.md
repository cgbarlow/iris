# SPEC-124-A: System Notification Banner

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-124-A |
| **ADR** | [ADR-124](../ADR-124-System-Notification-Banner.md) |
| **Status** | Approved |
| **Date** | 2026-04-21 |

## Overview

A single admin-posted free-text banner that renders as a sticky top
strip on every Iris page, visible to anonymous and authenticated users.
Reuses the existing `settings` table + admin-gated settings router (DRY)
and exposes a focused public GET so anonymous visitors can poll it.

## Backend

### Settings default

Add `"notification_banner_message": ""` to `DEFAULTS` in
`backend/app/settings/service.py`. Empty string = no banner. Admins
write to this key via the existing `PUT /api/settings/{key}` endpoint;
no new write path.

### Public read endpoint

New module `backend/app/notifications/router.py`:

```python
router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("/banner")
async def get_banner(request: Request) -> dict[str, str]:
    """Public endpoint: return the current system notification banner text.

    No auth required — this is visible to anonymous visitors
    (ADR-123 / ADR-124). Returns empty string when no banner is set.
    """
    db = request.app.state.db_manager.main_db
    setting = await get_setting(db, "notification_banner_message")
    return {"message": setting["value"] if setting else ""}
```

Register in `backend/app/main.py` alongside the other routers.

No other endpoints are needed — `GET/PUT /api/settings/*` continues to
authenticate; only this one focused endpoint is public.

## Frontend

### `SystemBanner.svelte` component

Location: `frontend/src/lib/components/SystemBanner.svelte`.

```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { apiFetch } from '$lib/utils/api';

  const POLL_MS = 60_000;
  const STORAGE_PREFIX = 'iris-banner-dismissed:';

  let message = $state('');
  let dismissed = $state(false);
  let pollTimer: ReturnType<typeof setInterval> | undefined;

  // Hash the message so dismiss is per-message (edit → reappears).
  function hashMsg(s: string): string {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    return Math.abs(h).toString(36);
  }

  async function load() {
    try {
      const data = await apiFetch<{ message: string }>('/api/notifications/banner');
      message = data.message ?? '';
      dismissed = message
        ? localStorage.getItem(STORAGE_PREFIX + hashMsg(message)) === '1'
        : false;
    } catch { /* silent — banner is non-critical */ }
  }

  function dismiss() {
    localStorage.setItem(STORAGE_PREFIX + hashMsg(message), '1');
    dismissed = true;
  }

  onMount(() => {
    load();
    pollTimer = setInterval(load, POLL_MS);
  });
  onDestroy(() => clearInterval(pollTimer));
</script>

{#if message && !dismissed}
  <div class="system-banner" role="status" aria-live="polite">
    <span>{message}</span>
    <button aria-label="Dismiss notification" onclick={dismiss}>×</button>
  </div>
{/if}
```

Styling: `position: sticky; top: 0; z-index: 40; background: var(--color-warning); color: var(--color-fg); padding: 0.5rem 1rem; display: flex; justify-content: space-between; align-items: center`. Uses existing theme vars; no new palette.

### AppShell integration

Mount `<SystemBanner />` at the top of `AppShell.svelte`, outside the
header flex container, so it sits above everything including the
application header. Visible to anonymous and authenticated users alike.

### Admin edit UI

Extend `frontend/src/routes/admin/settings/+page.svelte`: add a
`textarea` bound to `notification_banner_message`, a Save button that
calls the existing `PUT /api/settings/{key}` helper, and a small help
text ("Empty to clear"). No new API needed — the page already POSTs to
the generic settings endpoint.

### Escaping

Rendered as `{message}` (Svelte's default text interpolation, which
escapes HTML). Plain text only per ADR-124's decision — no Markdown, no
`{@html}`.

## Acceptance criteria

1. Admin sets `notification_banner_message="Hello world"` via the admin
   settings page. Within 60 s every open Iris tab (authenticated or
   anonymous) shows a sticky top banner with "Hello world".
2. Admin clears the message (empty string). Within 60 s the banner
   disappears on all tabs.
3. User clicks Dismiss — banner disappears for that tab immediately.
   Reopening the same tab (localStorage persists) keeps it dismissed.
   If the admin edits the message to something different, the new
   message re-appears (different hash).
4. Anonymous GET `/api/notifications/banner` → 200 with `{"message": "..."}`.
5. Anonymous PUT `/api/settings/notification_banner_message` → 401
   (admin-gated by the existing endpoint — unchanged).
6. Banner text renders as plain text; any `<script>` or HTML in the
   message is escaped by Svelte's default interpolation.

## Tests

- `backend/tests/test_notifications/test_banner.py`:
  - GET `/api/notifications/banner` with no auth → 200, `{"message": ""}`.
  - Admin PUTs the settings key → GET returns the new value.
  - Non-admin PUT returns 403 (covers existing behaviour, DRY).

- `frontend/tests/e2e/system-banner.spec.ts`:
  - Admin logs in, edits banner text on `/admin/settings`, saves.
  - Open a new anonymous browser context; `/` shows the banner text.
  - Click Dismiss → banner hidden; reload confirms dismissed state
    persists. Change the banner text as admin → new message
    re-appears on the anonymous tab.

## Out of scope

- Multiple banners / banner queue / banner history.
- Severity levels (info / warning / error / success colour variations).
  If desired later, store JSON instead of plain string and iterate.
- Expiry timestamps (banner auto-clears at T).
- Targeting (only show to role X or anonymous users).
- Realtime push — 60 s polling is the trade-off per ADR-124.
- Markdown / HTML — plain text only per ADR-124.
