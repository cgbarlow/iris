"""Audit logging service with hash chain per SPEC-007-A."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

GENESIS_HASH = hashlib.sha256(b"IRIS_AUDIT_GENESIS").hexdigest()


def compute_entry_hash(entry: dict[str, object], previous_hash: str) -> str:
    """Compute SHA-256 hash for an audit log entry."""
    payload = "|".join([
        str(entry["id"]),
        str(entry["timestamp"]),
        str(entry["user_id"]),
        str(entry["username"]),
        str(entry["action"]),
        str(entry["target_type"]),
        str(entry.get("target_id") or ""),
        str(entry.get("detail") or ""),
        str(entry.get("ip_address") or ""),
        str(entry.get("session_id") or ""),
        previous_hash,
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def write_audit_entry(
    db: aiosqlite.Connection,
    *,
    user_id: str,
    username: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    detail: dict[str, object] | None = None,
    ip_address: str | None = None,
    session_id: str | None = None,
) -> None:
    """Write a hash-chained audit log entry."""
    # 1. Get the previous entry's hash (or genesis hash)
    cursor = await db.execute(
        "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    previous_hash = row[0] if row else GENESIS_HASH

    # 2. Get next ID
    cursor = await db.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM audit_log"
    )
    next_id_row = await cursor.fetchone()
    next_id: int = next_id_row[0]  # type: ignore[index]

    # 3. Build entry
    timestamp = datetime.now(tz=UTC).isoformat()
    detail_json = json.dumps(detail) if detail else None

    entry: dict[str, object] = {
        "id": next_id,
        "timestamp": timestamp,
        "user_id": user_id,
        "username": username,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "detail": detail_json,
        "ip_address": ip_address,
        "session_id": session_id,
    }

    # 4. Compute hash
    entry_hash = compute_entry_hash(entry, previous_hash)

    # 5. Insert
    await db.execute(
        "INSERT INTO audit_log "
        "(id, timestamp, user_id, username, action, target_type, "
        "target_id, detail, ip_address, session_id, "
        "previous_hash, entry_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            next_id, timestamp, user_id, username, action,
            target_type, target_id, detail_json, ip_address,
            session_id, previous_hash, entry_hash,
        ),
    )
    await db.commit()


async def verify_audit_chain(
    db: aiosqlite.Connection,
) -> tuple[bool, int]:
    """Verify the audit log hash chain. Returns (is_valid, entries_checked)."""
    cursor = await db.execute(
        "SELECT id, timestamp, user_id, username, action, target_type, "
        "target_id, detail, ip_address, session_id, "
        "previous_hash, entry_hash "
        "FROM audit_log ORDER BY id ASC"
    )
    rows = await cursor.fetchall()

    if not rows:
        return True, 0

    expected_previous = GENESIS_HASH

    for row in rows:
        entry: dict[str, object] = {
            "id": row[0],
            "timestamp": row[1],
            "user_id": row[2],
            "username": row[3],
            "action": row[4],
            "target_type": row[5],
            "target_id": row[6],
            "detail": row[7],
            "ip_address": row[8],
            "session_id": row[9],
        }
        previous_hash: str = row[10]
        entry_hash: str = row[11]

        # Check previous_hash matches expected
        if previous_hash != expected_previous:
            return False, int(row[0])

        # Recompute entry_hash
        computed = compute_entry_hash(entry, previous_hash)
        if computed != entry_hash:
            return False, int(row[0])

        expected_previous = entry_hash

    return True, len(rows)
