# ADR-080: Edit Locking (Checkout) System

## Proposal: Pessimistic edit locking with 15-minute timeout and heartbeat

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-080 |
| **Initiative** | Multi-User Collaboration |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-05 |
| **Status** | Approved |
| **Dependencies** | ADR-071 |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris supporting multiple users editing diagrams, elements, and packages concurrently,

**facing** the problem that optimistic concurrency control (OCC via If-Match headers) only detects conflicts at save time, leading to lost work when two users edit simultaneously without awareness of each other,

**we decided for** advisory pessimistic locking with 15-minute timeout, heartbeat extension, lazy expiry cleanup, and UX-level coordination banners,

**and neglected** real-time collaborative editing (too complex), server-enforced locking on PUT/DELETE (too restrictive), and background lock cleanup jobs (unnecessary complexity),

**to achieve** clear UX signaling when another user is editing, prevention of accidental concurrent edits, and graceful lock recovery through timeout,

**accepting that** locks are advisory (OCC remains authoritative), abandoned locks persist up to 15 minutes, and the system requires client-side heartbeat for lock maintenance.

---

## Decisions

1. **Advisory locking**: Backend does NOT enforce lock on PUT/DELETE — OCC via If-Match remains authoritative
2. **15-minute timeout**: Locks expire after 15 minutes without heartbeat
3. **Lazy cleanup**: Expired locks are cleaned up on every lock operation — no background jobs
4. **Heartbeat**: Client sends heartbeat every 5 minutes to extend lock
5. **Auto-release**: Lock released on save, navigate away, or browser close (beforeunload)
6. **Re-acquire**: Acquiring your own lock refreshes it (idempotent)
7. **Admin force-release**: Admins can force-release any lock
8. **Target types**: diagram, element, package

---

## Specification

See [SPEC-080-A](specs/SPEC-080-A-Edit-Locking-Checkout.md).
