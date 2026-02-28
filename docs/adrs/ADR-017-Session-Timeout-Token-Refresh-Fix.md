# ADR-017: Session Timeout Token Refresh Fix

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-017 |
| **Initiative** | Fix Session Timeout Token Refresh |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris session timeout warning dialog (`SessionTimeoutWarning.svelte`) which calls `apiFetch('/api/auth/refresh', ...)` to extend the user's session when they click "Continue session", but discards the returned tokens without updating the auth store,

**facing** the bug where the refresh token is consumed server-side (marked `used_at` per refresh token rotation), but the old access and refresh tokens remain in the client auth store — causing the next API call's auto-refresh to use the consumed token, triggering token family revocation and forcing an unexpected logout,

**we decided for** reusing the existing `tryRefresh()` function from `api.ts` instead of raw `apiFetch` calls, since `tryRefresh()` already correctly calls `updateTokens()` to persist new tokens in the auth store and handles failure by calling `clearAuth()`,

**and neglected** fixing the `extendSession` function to manually parse and store the refresh response (duplicates logic already in `tryRefresh()`), and adding a new dedicated refresh endpoint or middleware (the existing infrastructure is correct, only the call site was wrong),

**to achieve** correct token rotation during session extension — the auth store is updated with fresh tokens, the warning timer resets based on the new token's expiry, and subsequent API calls use valid credentials,

**accepting that** this change makes `tryRefresh()` a public export from `api.ts`, broadening its API surface, which is acceptable since it is a stable, well-tested function that other components may legitimately need.

---

## Options Considered

### Option 1: Reuse existing tryRefresh() (Selected)

**Pros:**
- Zero logic duplication — `tryRefresh()` already handles token storage, error handling, and `clearAuth()`
- Single line change to export; minimal code change in `SessionTimeoutWarning.svelte`
- Maintains the existing deduplication logic (`refreshPromise`) for concurrent refresh attempts

**Cons:**
- Exports a previously private function, slightly broadening the module API

**Why selected:** The bug exists solely because the correct function was not used. Reusing it is the minimal, correct fix.

### Option 2: Fix extendSession to manually store tokens (Rejected)

**Pros:**
- Does not change the `api.ts` export surface

**Cons:**
- Duplicates token storage logic already in `tryRefresh()`
- More code to maintain and test
- Misses the `clearAuth()` on failure that `tryRefresh()` provides

**Why rejected:** Violates DRY and increases maintenance burden for no benefit.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement fix | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes auth store |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-017-A | Session Timeout Fix | Technical Specification | [specs/SPEC-017-A-Session-Timeout-Fix.md](specs/SPEC-017-A-Session-Timeout-Fix.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
