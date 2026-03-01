# ADR-031: Session Timeout During Active Use

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-031 |
| **Initiative** | Fix Session Timeout Popup During Active Use |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris session timeout warning component (`SessionTimeoutWarning.svelte`) which uses a Svelte 5 `$effect` to schedule a warning timer based on the JWT `exp` claim at login time,

**facing** the bug where the timeout popup appears during active use because the `$effect` does not reliably reschedule its timer when `apiFetch` silently auto-refreshes the token after a 401 response — the auto-refresh calls `updateTokens()` which writes to the `$state` variable, but the `$effect`'s dependency on the token value through the `getAccessToken()` function indirection may not trigger a re-run in all async execution contexts, leaving the original timer (based on the old token's expiry) to fire even though the user has a fresh session,

**we decided for** making the token dependency in the `$effect` explicit by reading `getAccessToken()` into a local variable at the top of the effect (before any early returns) and using that value for JWT parsing, ensuring Svelte 5's fine-grained reactivity consistently tracks the `$state` read and re-runs the effect whenever `updateTokens()` or `setAuth()` writes a new token,

**and neglected** adding a separate event-based notification system where `apiFetch` emits a custom event or calls a callback when auto-refresh occurs (introduces coupling between the API layer and UI components, adds a parallel notification channel alongside the existing reactive store), and polling the token expiry on a periodic interval (wasteful, imprecise, and defeats the purpose of reactive programming),

**to achieve** correct timer rescheduling whenever the JWT is refreshed — whether by user-initiated session extension or by silent auto-refresh during active API use — so the warning popup only appears when the session is genuinely about to expire,

**accepting that** this is a minimal change that relies on Svelte 5's reactive dependency tracking working correctly for `$state` reads inside `$effect`, which is the documented and intended behaviour of the runes API.

---

## Options Considered

### Option 1: Explicit token dependency in $effect (Selected)

Ensure the `$effect` reads `getAccessToken()` into a local variable before any conditional branches, guaranteeing Svelte tracks the dependency.

**Pros:**
- Minimal code change — one variable assignment
- Uses the existing reactive primitives as designed
- No new abstractions or coupling introduced
- Cleanup function already correctly clears old timers on re-run

**Cons:**
- Relies on Svelte 5's dependency tracking (well-documented behaviour)

**Why selected:** The root cause is that the `$effect` may not consistently track the `$state` dependency through the function call. Making the read explicit is the idiomatic Svelte 5 fix and requires the smallest change.

### Option 2: Event-based auto-refresh notification (Rejected)

Have `apiFetch` emit a custom event or call a registered callback when auto-refresh succeeds, allowing `SessionTimeoutWarning` to reset its timer in response.

**Pros:**
- Decouples timer logic from reactive dependency tracking
- Explicit control flow

**Cons:**
- Introduces a parallel notification channel alongside the reactive store
- Couples `api.ts` to UI component concerns
- More code to write and maintain
- Violates the existing pattern where components react to store state, not events

**Why rejected:** Adds unnecessary complexity and coupling. The reactive store is the correct abstraction for this use case.

### Option 3: Periodic token expiry polling (Rejected)

Use `setInterval` to check the token's `exp` claim every N seconds and reschedule the warning timer if the expiry has changed.

**Pros:**
- Does not depend on reactive tracking
- Simple to understand

**Cons:**
- Wasteful — polls even when nothing has changed
- Imprecise timing — warning may appear late or early depending on poll interval
- Defeats the purpose of Svelte's reactive system
- Additional interval to manage and clean up

**Why rejected:** Polling is an anti-pattern when reactive state is available.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement fix | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes auth store |
| Supersedes | ADR-017 | Session Timeout Token Refresh Fix | ADR-017 fixed the "Continue session" button; this ADR fixes the complementary bug where auto-refresh during active use does not reschedule the timer |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-031-A | Session Timeout Active Use Fix | Technical Specification | [specs/SPEC-031-A-Session-Timeout-Active-Use.md](specs/SPEC-031-A-Session-Timeout-Active-Use.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
