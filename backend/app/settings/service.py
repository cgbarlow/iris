"""Settings service for admin-configurable parameters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

# Default settings values
DEFAULTS = {
    "session_timeout_minutes": "15",
    "gallery_thumbnail_mode": "svg",
}


async def seed_defaults(db: aiosqlite.Connection) -> None:
    """Seed default settings if they don't exist."""
    for key, value in DEFAULTS.items():
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    await db.commit()


async def get_all_settings(db: aiosqlite.Connection) -> list[dict[str, object]]:
    """Get all settings."""
    cursor = await db.execute(
        "SELECT key, value, updated_at, updated_by FROM settings ORDER BY key"
    )
    rows = await cursor.fetchall()
    return [
        {"key": r[0], "value": r[1], "updated_at": r[2], "updated_by": r[3]}
        for r in rows
    ]


async def get_setting(db: aiosqlite.Connection, key: str) -> dict[str, object] | None:
    """Get a single setting by key."""
    cursor = await db.execute(
        "SELECT key, value, updated_at, updated_by FROM settings WHERE key = ?",
        (key,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {"key": row[0], "value": row[1], "updated_at": row[2], "updated_by": row[3]}


async def update_setting(
    db: aiosqlite.Connection, key: str, value: str, updated_by: str
) -> dict[str, object] | None:
    """Update a setting. Returns None if key doesn't exist."""
    cursor = await db.execute("SELECT key FROM settings WHERE key = ?", (key,))
    if await cursor.fetchone() is None:
        return None

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE settings SET value = ?, updated_at = ?, updated_by = ? WHERE key = ?",
        (value, now, updated_by, key),
    )
    await db.commit()
    return {"key": key, "value": value, "updated_at": now, "updated_by": updated_by}
