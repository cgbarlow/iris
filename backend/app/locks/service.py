"""Edit lock service with lazy expiry cleanup (ADR-080)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

LOCK_DURATION_MINUTES = 15


async def cleanup_expired_locks(db: aiosqlite.Connection) -> int:
    """Remove expired locks. Returns count deleted."""
    now = datetime.now(tz=UTC).isoformat()
    cursor = await db.execute(
        "DELETE FROM edit_locks WHERE expires_at < ?", (now,)
    )
    await db.commit()
    return cursor.rowcount


async def acquire_lock(
    db: aiosqlite.Connection,
    *,
    target_type: str,
    target_id: str,
    user_id: str,
    username: str,
) -> dict:
    """Acquire or refresh a lock. Returns lock dict or conflict info."""
    await cleanup_expired_locks(db)

    now = datetime.now(tz=UTC)
    expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)

    # Check existing lock
    cursor = await db.execute(
        "SELECT id, user_id, username, acquired_at, expires_at, last_heartbeat "
        "FROM edit_locks WHERE target_type = ? AND target_id = ?",
        (target_type, target_id),
    )
    existing = await cursor.fetchone()

    if existing:
        if existing[1] == user_id:
            # Re-acquiring own lock — refresh it
            await db.execute(
                "UPDATE edit_locks SET expires_at = ?, last_heartbeat = ? WHERE id = ?",
                (expires_at.isoformat(), now.isoformat(), existing[0]),
            )
            await db.commit()
            return {
                "lock": {
                    "id": existing[0],
                    "target_type": target_type,
                    "target_id": target_id,
                    "user_id": user_id,
                    "username": username,
                    "acquired_at": existing[3],
                    "expires_at": expires_at.isoformat(),
                    "last_heartbeat": now.isoformat(),
                },
            }
        # Held by another user — conflict
        return {
            "conflict": True,
            "lock": {
                "id": existing[0],
                "target_type": target_type,
                "target_id": target_id,
                "user_id": existing[1],
                "username": existing[2],
                "acquired_at": existing[3],
                "expires_at": existing[4],
                "last_heartbeat": existing[5],
            },
        }

    # No existing lock — create one
    lock_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO edit_locks "
        "(id, target_type, target_id, user_id, username, acquired_at, expires_at, last_heartbeat) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (lock_id, target_type, target_id, user_id, username,
         now.isoformat(), expires_at.isoformat(), now.isoformat()),
    )
    await db.commit()
    return {
        "lock": {
            "id": lock_id,
            "target_type": target_type,
            "target_id": target_id,
            "user_id": user_id,
            "username": username,
            "acquired_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_heartbeat": now.isoformat(),
        },
    }


async def check_lock(
    db: aiosqlite.Connection,
    *,
    target_type: str,
    target_id: str,
    user_id: str,
) -> dict:
    """Check whether a target is locked."""
    await cleanup_expired_locks(db)

    cursor = await db.execute(
        "SELECT id, target_type, target_id, user_id, username, "
        "acquired_at, expires_at, last_heartbeat "
        "FROM edit_locks WHERE target_type = ? AND target_id = ?",
        (target_type, target_id),
    )
    row = await cursor.fetchone()
    if row is None:
        return {"locked": False, "lock": None, "is_owner": False}

    lock = {
        "id": row[0],
        "target_type": row[1],
        "target_id": row[2],
        "user_id": row[3],
        "username": row[4],
        "acquired_at": row[5],
        "expires_at": row[6],
        "last_heartbeat": row[7],
    }
    return {
        "locked": True,
        "lock": lock,
        "is_owner": row[3] == user_id,
    }


async def heartbeat_lock(
    db: aiosqlite.Connection,
    lock_id: str,
    user_id: str,
) -> dict | None:
    """Extend a lock's expiry. Returns updated lock or None."""
    cursor = await db.execute(
        "SELECT user_id FROM edit_locks WHERE id = ?", (lock_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    if row[0] != user_id:
        return None

    now = datetime.now(tz=UTC)
    expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)
    await db.execute(
        "UPDATE edit_locks SET expires_at = ?, last_heartbeat = ? WHERE id = ?",
        (expires_at.isoformat(), now.isoformat(), lock_id),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT id, target_type, target_id, user_id, username, "
        "acquired_at, expires_at, last_heartbeat "
        "FROM edit_locks WHERE id = ?",
        (lock_id,),
    )
    r = await cursor.fetchone()
    return {
        "id": r[0], "target_type": r[1], "target_id": r[2],
        "user_id": r[3], "username": r[4], "acquired_at": r[5],
        "expires_at": r[6], "last_heartbeat": r[7],
    }


async def release_lock(
    db: aiosqlite.Connection,
    lock_id: str,
    user_id: str,
) -> bool:
    """Release a lock (owner only). Returns True if released."""
    cursor = await db.execute(
        "SELECT user_id FROM edit_locks WHERE id = ?", (lock_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return False
    if row[0] != user_id:
        return False

    await db.execute("DELETE FROM edit_locks WHERE id = ?", (lock_id,))
    await db.commit()
    return True


async def force_release_lock(
    db: aiosqlite.Connection,
    lock_id: str,
) -> bool:
    """Force-release a lock (admin). Returns True if released."""
    cursor = await db.execute(
        "SELECT id FROM edit_locks WHERE id = ?", (lock_id,)
    )
    if await cursor.fetchone() is None:
        return False

    await db.execute("DELETE FROM edit_locks WHERE id = ?", (lock_id,))
    await db.commit()
    return True


async def list_active_locks(db: aiosqlite.Connection) -> list[dict]:
    """List all non-expired locks."""
    await cleanup_expired_locks(db)

    cursor = await db.execute(
        "SELECT id, target_type, target_id, user_id, username, "
        "acquired_at, expires_at, last_heartbeat "
        "FROM edit_locks ORDER BY acquired_at DESC"
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0], "target_type": r[1], "target_id": r[2],
            "user_id": r[3], "username": r[4], "acquired_at": r[5],
            "expires_at": r[6], "last_heartbeat": r[7],
        }
        for r in rows
    ]
