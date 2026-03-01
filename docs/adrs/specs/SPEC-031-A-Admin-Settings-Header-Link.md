# SPEC-031-A: Admin Settings Header Link

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-031-A |
| **ADR Reference** | [ADR-031: Admin Settings Header Link](../ADR-031-Admin-Settings-Header-Link.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification defines the implementation of an admin-only "Settings" link in the application header bar, positioned before the existing "Help" link.

---

## A. Header Modification

### File: `frontend/src/lib/components/AppShell.svelte`

In the header's right-side `<div class="flex items-center gap-4">` area, add a conditional link before the Help link:

```svelte
{#if getCurrentUser()?.role === 'admin'}
	<a
		href="/admin/settings"
		class="rounded px-2 py-1 text-sm"
		style="color: var(--color-muted)"
		aria-label="Admin Settings"
	>
		Settings
	</a>
{/if}
```

### Placement

The element order in the header right section becomes:

| Position | Element | Condition |
|----------|---------|-----------|
| 1 | Settings link | Admin role only |
| 2 | Help link | Always |
| 3 | Username text | Authenticated |
| 4 | Sign out button | Authenticated |

### Styling

- Uses the same CSS classes and inline style as the existing Help link: `class="rounded px-2 py-1 text-sm"` with `style="color: var(--color-muted)"`
- Uses `aria-label="Admin Settings"` to distinguish from the user Settings page link in the sidebar

---

## B. Role Check

The existing `getCurrentUser()` import from `$lib/stores/auth.svelte.js` is already available in AppShell.svelte. The admin check uses the same pattern as the sidebar admin section: `getCurrentUser()?.role === 'admin'`.

No additional imports are needed.

---

## C. E2E Tests

### File: `frontend/tests/e2e/navigation.spec.ts`

Two new tests added to the existing Navigation describe block:

1. **Admin sees Settings link in header** — Log in as admin, verify the header contains a "Settings" link pointing to `/admin/settings`.
2. **Non-admin does not see Settings link in header** — Create a viewer user via API, log in as that user, verify the header does not contain the admin Settings link.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Settings link visible in header for admin | Log in as admin; verify link with text "Settings" and href `/admin/settings` in header |
| Settings link not visible for non-admin | Log in as viewer; verify no Settings link in header |
| Settings link navigates to admin settings page | Click Settings link in header; verify URL is `/admin/settings` and heading is "Settings" |
| Settings link positioned before Help | Verify Settings link appears before Help link in DOM order |
| Help link still works | Existing Help link test continues to pass |
| Sidebar admin section unchanged | Existing sidebar admin section tests continue to pass |

---

*This specification implements [ADR-031](../ADR-031-Admin-Settings-Header-Link.md).*
