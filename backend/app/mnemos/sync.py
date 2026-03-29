"""MNEMOS data synchronization (ADR-111).

Provides per-entity sync hooks and bulk reindex for keeping MNEMOS engrams
in sync with Iris database entities. Sync is fire-and-forget — failures are
logged but never block the main mutation path.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

log = logging.getLogger("app.mnemos.sync")


async def _get_mnemos_client() -> Any | None:
    """Create a MNEMOS SDK client from extension config, or None if unavailable."""
    try:
        from mnemos_sdk import MnemosClient, MnemosConfig  # type: ignore[import-untyped]

        # Will be configured properly when called with db context
        return MnemosClient, MnemosConfig
    except ImportError:
        log.debug("mnemos_sdk not installed")
        return None


async def _get_client_from_config(db: DatabasePort) -> Any | None:
    """Create a configured MNEMOS client from the extensions table."""
    try:
        from app.extensions.service import get_extension, is_extension_enabled

        if not await is_extension_enabled(db, "mnemos"):
            return None

        ext = await get_extension(db, "mnemos")
        if ext is None:
            return None

        config = ext.get("config", {})
        url = config.get("url", "http://localhost:8700") if isinstance(config, dict) else "http://localhost:8700"
        timeout = config.get("timeout_ms", 5000) if isinstance(config, dict) else 5000

        from mnemos_sdk import MnemosClient, MnemosConfig  # type: ignore[import-untyped]

        sdk_config = MnemosConfig(base_url=str(url), timeout_s=int(timeout) / 1000)
        return MnemosClient(sdk_config)
    except Exception:  # noqa: BLE001
        log.debug("Failed to create MNEMOS client", exc_info=True)
        return None


async def sync_engram(
    db: DatabasePort,
    engram: dict[str, Any],
) -> None:
    """Index a single engram to MNEMOS. Fire-and-forget — logs on failure."""
    try:
        client = await _get_client_from_config(db)
        if client is None:
            return
        client.index([engram])
        log.debug("Synced engram: %s", engram.get("source", "unknown"))
    except Exception:  # noqa: BLE001
        log.warning("Failed to sync engram to MNEMOS", exc_info=True)


async def delete_engram(
    db: DatabasePort,
    source_uri: str,
) -> None:
    """Delete an engram from MNEMOS by source URI. Fire-and-forget."""
    try:
        client = await _get_client_from_config(db)
        if client is None:
            return
        # MNEMOS delete by engram ID — we'd need to search by source first
        # For now, log intent; full implementation requires MNEMOS search-by-source API
        log.debug("Would delete engram with source: %s", source_uri)
    except Exception:  # noqa: BLE001
        log.warning("Failed to delete engram from MNEMOS", exc_info=True)


async def bulk_reindex(db: DatabasePort) -> dict[str, int]:
    """Reindex all Iris entities into MNEMOS. Returns counts.

    This is called from the admin reindex endpoint.
    """
    from app.mnemos.engram_mapper import build_all_engrams

    t0 = time.monotonic()
    engrams = await build_all_engrams(db)

    client = await _get_client_from_config(db)
    if client is None:
        return {"indexed": 0, "errors": 0, "duration_ms": 0}

    indexed = 0
    errors = 0

    # Index in batches of 50
    batch_size = 50
    for i in range(0, len(engrams), batch_size):
        batch = engrams[i : i + batch_size]
        try:
            client.index(batch)
            indexed += len(batch)
        except Exception:  # noqa: BLE001
            log.warning("Failed to index batch %d-%d", i, i + len(batch), exc_info=True)
            errors += len(batch)

    duration_ms = int((time.monotonic() - t0) * 1000)
    log.info("Bulk reindex complete: indexed=%d errors=%d duration=%dms", indexed, errors, duration_ms)

    return {"indexed": indexed, "errors": errors, "duration_ms": duration_ms}


async def sync_element_hook(
    db: DatabasePort,
    element_id: str,
    element_type: str,
    name: str,
    description: str | None,
    data: dict[str, Any] | None,
    set_id: str | None,
) -> None:
    """Sync hook called after element create/update. Fire-and-forget."""
    from app.mnemos.engram_mapper import element_to_engram

    engram = element_to_engram(element_id, element_type, name, description, data, set_id)
    await sync_engram(db, engram)


async def sync_element_delete_hook(
    db: DatabasePort,
    element_id: str,
) -> None:
    """Sync hook called after element delete. Fire-and-forget."""
    await delete_engram(db, f"iris://elements/{element_id}")


async def sync_relationship_hook(
    db: DatabasePort,
    rel_id: str,
    relationship_type: str,
    source_name: str,
    target_name: str,
    label: str | None,
    set_id: str | None,
) -> None:
    """Sync hook called after relationship create/update. Fire-and-forget."""
    from app.mnemos.engram_mapper import relationship_to_engram

    engram = relationship_to_engram(rel_id, relationship_type, source_name, target_name, label, set_id)
    await sync_engram(db, engram)


async def sync_diagram_hook(
    db: DatabasePort,
    diagram_id: str,
    diagram_type: str,
    name: str,
    description: str | None,
    set_id: str | None,
    package_id: str | None,
) -> None:
    """Sync hook called after diagram create/update. Fire-and-forget."""
    from app.mnemos.engram_mapper import diagram_to_engram

    engram = diagram_to_engram(diagram_id, diagram_type, name, description, set_id, package_id)
    await sync_engram(db, engram)
