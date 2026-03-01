# SPEC-031-A: Session Timeout Active Use Fix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-031-A |
| **ADR Reference** | [ADR-031: Session Timeout During Active Use](../ADR-031-Session-Timeout-During-Active-Use.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification describes the fix for the session timeout warning popup appearing during active use. The root cause is that the `$effect` in `SessionTimeoutWarning.svelte` does not reliably reschedule its timer when the JWT is silently refreshed by `apiFetch`'s auto-refresh mechanism.

---

## Root Cause Analysis

The `SessionTimeoutWarning.svelte` component's `$effect` schedules a `setTimeout` based on the JWT's `exp` claim:

1. User logs in, `setAuth()` stores tokens in `$state` variables
2. `$effect` runs, reads `getAccessToken()`, parses JWT, schedules warning timer for 60s before expiry
3. User works actively, making API calls via `apiFetch()`
4. A 401 response triggers `apiFetch`'s auto-refresh logic
5. `tryRefresh()` calls `updateTokens()`, writing the new token to the `$state` variable `accessToken`
6. **Bug:** The `$effect` does not consistently re-run to reschedule the timer with the new token's expiry
7. The old timer fires, showing the timeout warning even though the session was just refreshed

The issue is that the `$effect`'s dependency on `getAccessToken()` may not be tracked reliably across all execution contexts. In the current code, the `$effect` calls `isAuthenticated()` first (line 16), and if that returns false, it returns early before ever calling `getAccessToken()`. This means on runs where `isAuthenticated()` is false, the effect does NOT track the `accessToken` state. More critically, the function-call indirection may not always register as a tracked dependency in edge cases.

---

## Changes

### A. Update SessionTimeoutWarning.svelte $effect

**File:** `frontend/src/lib/components/SessionTimeoutWarning.svelte`

Make the token dependency explicit by reading `getAccessToken()` into a local variable at the top of the `$effect`, before any conditional logic:

```typescript
$effect(() => {
    // Read token FIRST to ensure Svelte tracks the $state dependency.
    // This must happen before any early returns so the effect re-runs
    // whenever updateTokens() or setAuth() writes a new token value.
    const token = getAccessToken();

    if (!isAuthenticated()) return;
    if (!token) return;

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expiresAt = payload.exp * 1000;
        const warningTime = expiresAt - 60_000;
        const now = Date.now();

        if (warningTime > now) {
            timeoutId = setTimeout(() => {
                showWarning = true;
                secondsRemaining = 60;
                intervalId = setInterval(() => {
                    secondsRemaining--;
                    if (secondsRemaining <= 0) {
                        clearInterval(intervalId);
                    }
                }, 1000);
            }, warningTime - now);
        }
    } catch {
        // Invalid token — ignore
    }

    return () => {
        if (timeoutId) clearTimeout(timeoutId);
        if (intervalId) clearInterval(intervalId);
    };
});
```

**Key change:** `const token = getAccessToken()` is now the FIRST statement in the effect, before the `isAuthenticated()` check. This guarantees that the `$state` read of `accessToken` is always tracked, regardless of which branch the effect takes.

### B. Verify auth store reactivity (No changes needed)

**File:** `frontend/src/lib/stores/auth.svelte.ts`

Verification confirms that `accessToken` is declared with `$state` and that `updateTokens()` writes to it directly:

```typescript
let accessToken = $state<string | null>(initial?.accessToken ?? null);

export function getAccessToken(): string | null {
    return accessToken;  // reads $state — tracked in $effect
}

export function updateTokens(tokens: AuthTokens): void {
    accessToken = tokens.access_token;  // writes $state — triggers $effect re-run
    ...
}
```

No changes needed to the auth store — it is already correctly reactive.

### C. Verify apiFetch auto-refresh (No changes needed)

**File:** `frontend/src/lib/utils/api.ts`

The auto-refresh in `apiFetch` already calls `tryRefresh()` which calls `updateTokens()`. No changes needed.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| `$effect` reads `getAccessToken()` before any early return | Code review confirms `const token = getAccessToken()` is the first statement |
| Timer reschedules when token is refreshed via `updateTokens()` | Vitest: verify old timer is cleared and new timer is scheduled when token changes |
| Timer reschedules when token is refreshed via `setAuth()` | Vitest: verify timer reschedules on `setAuth()` call |
| Warning does not show when user is actively working | The timer always reflects the latest token's expiry |
| Existing "Continue session" flow still works | Existing tests pass; `extendSession()` calls `tryRefresh()` which triggers the effect |
| Cleanup function clears all timers | Vitest: verify `clearTimeout` and `clearInterval` are called on effect re-run |

---

*This specification implements [ADR-031](../ADR-031-Session-Timeout-During-Active-Use.md).*
