# SPEC-017-A: Session Timeout Fix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-017-A |
| **ADR Reference** | [ADR-017: Session Timeout Token Refresh Fix](../ADR-017-Session-Timeout-Token-Refresh-Fix.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification describes the fix for the session timeout "Continue session" button failing to persist refreshed tokens, causing unexpected logout after the user extends their session.

---

## Root Cause Analysis

The `SessionTimeoutWarning.svelte` component's `extendSession()` function calls `apiFetch('/api/auth/refresh', ...)` directly, which:

1. Sends the refresh token to the server
2. Server rotates the token (marks old token `used_at`, issues new pair)
3. Response contains new `access_token` and `refresh_token`
4. **Bug:** `extendSession()` discards the response — tokens are never stored
5. Auth store retains the old (now consumed) tokens
6. Next API call triggers auto-refresh with the consumed refresh token
7. Server detects reuse of a consumed token, revokes the entire token family
8. User is logged out unexpectedly

---

## Changes

### A. Export tryRefresh from api.ts

**File:** `frontend/src/lib/utils/api.ts`

Add `export` keyword to the existing `tryRefresh()` function (line 23):

```typescript
export async function tryRefresh(): Promise<boolean> {
```

This function already:
- Reads the refresh token from the auth store
- Sends `POST /api/auth/refresh` with the token
- On success: calls `updateTokens()` to persist new tokens
- On failure: calls `clearAuth()` to clean up

No logic changes needed — the function is correct as-is.

### B. Update SessionTimeoutWarning.svelte

**File:** `frontend/src/lib/components/SessionTimeoutWarning.svelte`

**Import changes:**
- Remove: `import { apiFetch } from '$lib/utils/api'`
- Remove: `getRefreshToken` from auth store imports (no longer needed)
- Add: `import { tryRefresh } from '$lib/utils/api'`
- Add: `clearAuth` to auth store imports

**Replace `extendSession()` function:**

```typescript
async function extendSession() {
    const success = await tryRefresh();
    if (success) {
        // Re-schedule warning timer with new token's expiry
        if (timeoutId) clearTimeout(timeoutId);
        if (intervalId) clearInterval(intervalId);
        showWarning = false;
        // The $effect watching isAuthenticated/getAccessToken will re-schedule
    } else {
        clearAuth();
        showWarning = false;
        if (intervalId) clearInterval(intervalId);
    }
}
```

**Behaviour after fix:**
- On success: `tryRefresh()` updates tokens in auth store, warning is dismissed, `$effect` re-fires due to `getAccessToken()` change and schedules a new warning timer for the new token's expiry
- On failure: `clearAuth()` logs the user out, warning is dismissed

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| `tryRefresh` is exported from `api.ts` | Unit test imports `tryRefresh` and verifies it is a function |
| `SessionTimeoutWarning` uses `tryRefresh` instead of `apiFetch` | Code review confirms no `apiFetch` import in the component |
| Auth store is updated after session extension | `tryRefresh()` calls `updateTokens()` (verified by existing `tryRefresh` implementation) |
| Failed refresh clears auth | `extendSession()` calls `clearAuth()` on failure path |
| Warning timer resets after extension | `$effect` re-fires when `getAccessToken()` changes, scheduling new timeout |
| No `getRefreshToken` import in component | Component delegates token handling entirely to `tryRefresh()` |

---

*This specification implements [ADR-017](../ADR-017-Session-Timeout-Token-Refresh-Fix.md).*
