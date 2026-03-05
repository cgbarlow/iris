# SPEC-080-A: Edit Locking (Checkout) System

## Overview

Implements ADR-080: pessimistic advisory edit locking for multi-user collaboration.

## Database Schema

```sql
CREATE TABLE edit_locks (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL CHECK (target_type IN ('diagram', 'element', 'package')),
    target_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL,
    UNIQUE (target_type, target_id)
);
```

## API Endpoints

- `POST /api/locks` — Acquire lock (body: target_type, target_id). Returns 200 with lock or 409 with holder info
- `GET /api/locks/check?target_type=X&target_id=Y` — Check lock status
- `PUT /api/locks/{lock_id}/heartbeat` — Extend lock by 15 minutes
- `DELETE /api/locks/{lock_id}` — Release lock (owner only)
- `GET /api/locks` — List all active locks (admin)
- `DELETE /api/admin/locks/{lock_id}` — Force-release lock (admin)

## Lock Lifecycle

1. User clicks "Edit" → `POST /api/locks` with target_type and target_id
2. If success (200): enter edit mode, start heartbeat interval (every 5 min)
3. If conflict (409): show read-only banner with lock holder's username
4. While editing: heartbeat extends expires_at by 15 min from now
5. On save/navigate/close: `DELETE /api/locks/{lock_id}`, stop heartbeat
6. If heartbeat stops: lock expires after 15 min, other users can acquire

## Frontend Integration

- `createLockManager(targetType, targetId)` composable in `locks.svelte.ts`
- Auto-release via `beforeunload` and SvelteKit `beforeNavigate`
- Banner: "This {type} is being edited by {username}. You can view it in read-only mode."
- Admin locks page at `/admin/locks` with force-release capability

## Constants

- `LOCK_DURATION_MINUTES = 15`
- Heartbeat interval: 5 minutes (300,000 ms)
