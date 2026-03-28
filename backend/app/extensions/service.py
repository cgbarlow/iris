"""Extension registry service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


def _row_to_dict(row: tuple) -> dict[str, object]:
    """Convert an extensions row to a dict."""
    config_raw = row[8]
    config = json.loads(config_raw) if isinstance(config_raw, str) else (config_raw or {})
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "version": row[3],
        "is_enabled": bool(row[4]),
        "installed_at": row[5],
        "installed_by": row[6],
        "updated_at": row[7],
        "config": config,
    }


async def install_extension(
    db: DatabasePort,
    *,
    extension_id: str,
    name: str,
    description: str | None,
    version: str,
    installed_by: str,
    config: dict[str, object] | None = None,
) -> dict[str, object]:
    """Install (register) an extension."""
    now = datetime.now(tz=UTC).isoformat()
    config_json = json.dumps(config or {})

    await db.execute(
        "INSERT INTO extensions (id, name, description, version, is_enabled, "
        "installed_at, installed_by, updated_at, config) "
        "VALUES (?, ?, ?, ?, TRUE, ?, ?, ?, ?)",
        (extension_id, name, description, version, now, installed_by, now, config_json),
    )
    await db.commit()

    return {
        "id": extension_id,
        "name": name,
        "description": description,
        "version": version,
        "is_enabled": True,
        "installed_at": now,
        "installed_by": installed_by,
        "updated_at": now,
        "config": config or {},
    }


async def uninstall_extension(
    db: DatabasePort,
    extension_id: str,
) -> bool:
    """Uninstall (remove) an extension. Returns True if found and removed."""
    cursor = await db.execute(
        "SELECT id FROM extensions WHERE id = ?",
        (extension_id,),
    )
    if await cursor.fetchone() is None:
        return False

    await db.execute("DELETE FROM extensions WHERE id = ?", (extension_id,))
    await db.commit()
    return True


async def enable_extension(
    db: DatabasePort,
    extension_id: str,
) -> dict[str, object] | None:
    """Enable an extension. Returns updated dict, or None if not found."""
    cursor = await db.execute(
        "SELECT id FROM extensions WHERE id = ?",
        (extension_id,),
    )
    if await cursor.fetchone() is None:
        return None

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H:%M:%S")
    await db.execute(
        "UPDATE extensions SET is_enabled = TRUE, updated_at = ? WHERE id = ?",
        (now, extension_id),
    )
    await db.commit()
    return await get_extension(db, extension_id)


async def disable_extension(
    db: DatabasePort,
    extension_id: str,
) -> dict[str, object] | None:
    """Disable an extension. Returns updated dict, or None if not found."""
    cursor = await db.execute(
        "SELECT id FROM extensions WHERE id = ?",
        (extension_id,),
    )
    if await cursor.fetchone() is None:
        return None

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H:%M:%S")
    await db.execute(
        "UPDATE extensions SET is_enabled = FALSE, updated_at = ? WHERE id = ?",
        (now, extension_id),
    )
    await db.commit()
    return await get_extension(db, extension_id)


async def get_extension(
    db: DatabasePort,
    extension_id: str,
) -> dict[str, object] | None:
    """Get a single extension by ID."""
    cursor = await db.execute(
        "SELECT id, name, description, version, is_enabled, "
        "installed_at, installed_by, updated_at, config "
        "FROM extensions WHERE id = ?",
        (extension_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


async def list_extensions(
    db: DatabasePort,
) -> list[dict[str, object]]:
    """List all installed extensions."""
    cursor = await db.execute(
        "SELECT id, name, description, version, is_enabled, "
        "installed_at, installed_by, updated_at, config "
        "FROM extensions ORDER BY name",
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(row) for row in rows]


async def is_extension_enabled(
    db: DatabasePort,
    extension_id: str,
) -> bool:
    """Check if an extension is installed and enabled."""
    cursor = await db.execute(
        "SELECT is_enabled FROM extensions WHERE id = ?",
        (extension_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return False
    return bool(row[0])
