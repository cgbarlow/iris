"""Service layer for AI model management (ADR-093).

CRUD for providers, Q&A orchestration, usage logging, conversation storage.
Pattern follows themes/service.py and settings/service.py.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.ai.client import create_ai_client
from app.ai.context import build_set_context
from app.ai.models import ProviderTestResult

# Re-export for router convenience
build_context = build_set_context

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort


def _row_to_provider(row: tuple[object, ...]) -> dict[str, object]:
    """Map a DB row to a provider dict. api_key value is never exposed."""
    params_raw = row[7]
    params = json.loads(str(params_raw)) if params_raw else {}
    return {
        "id": row[0],
        "name": row[1],
        "provider_type": row[2],
        "base_url": row[3],
        # api_key is at row[4] — stored but never returned to callers
        # has_api_key tells callers whether a key exists without revealing it
        "has_api_key": bool(row[4]),
        "model": row[5],
        "system_prompt": row[6],
        "parameters": params,
        "timeout_ms": row[8],
        "retries": row[9],
        "is_default": bool(row[10]),
        "is_active": bool(row[11]),
        "created_by": row[12],
        "created_at": row[13],
        "updated_at": row[14],
    }


def _row_to_provider_with_key(row: tuple[object, ...]) -> dict[str, object]:
    """Like _row_to_provider but includes the raw api_key for internal use (client creation)."""
    result = _row_to_provider(row)
    result["api_key"] = row[4]  # only used internally, never sent to clients
    return result


_SELECT = (
    "SELECT id, name, provider_type, base_url, api_key, model, "
    "system_prompt, parameters, timeout_ms, retries, is_default, is_active, "
    "created_by, created_at, updated_at FROM ai_providers"
)


async def create_provider(
    db: DatabasePort,
    *,
    name: str,
    provider_type: str,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str,
    parameters: dict[str, object] | None = None,
    system_prompt: str | None = None,
    timeout_ms: int = 30000,
    retries: int = 3,
    is_default: bool = False,
    is_active: bool = True,
    created_by: str | None = None,
) -> dict[str, object]:
    """Create a new AI provider. If is_default, clears previous default."""
    if is_default:
        await db.execute(
            "UPDATE ai_providers SET is_default = 0, updated_at = ?",
            (datetime.now(tz=UTC).isoformat(),),
        )

    provider_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO ai_providers "
        "(id, name, provider_type, base_url, api_key, model, parameters, "
        "system_prompt, timeout_ms, retries, is_default, is_active, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            provider_id, name, provider_type, base_url, api_key or None, model,
            json.dumps(parameters or {}), system_prompt, timeout_ms, retries,
            int(is_default), int(is_active), created_by, now, now,
        ),
    )
    await db.commit()
    row = await (await db.execute(f"{_SELECT} WHERE id = ?", (provider_id,))).fetchone()
    return _row_to_provider(row)  # type: ignore[arg-type]


async def get_provider(
    db: DatabasePort,
    provider_id: str,
) -> dict[str, object] | None:
    """Get a single provider by ID."""
    row = await (await db.execute(f"{_SELECT} WHERE id = ?", (provider_id,))).fetchone()
    return _row_to_provider(row) if row else None


async def list_providers(
    db: DatabasePort,
    *,
    active_only: bool = False,
) -> list[dict[str, object]]:
    """List all providers, optionally filtered to active only."""
    if active_only:
        cursor = await db.execute(
            f"{_SELECT} WHERE is_active = 1 ORDER BY is_default DESC, name ASC"
        )
    else:
        cursor = await db.execute(
            f"{_SELECT} ORDER BY is_default DESC, name ASC"
        )
    rows = await cursor.fetchall()
    return [_row_to_provider(r) for r in rows]


async def update_provider(
    db: DatabasePort,
    provider_id: str,
    *,
    name: str,
    provider_type: str,
    base_url: str | None = None,
    api_key: str | None = None,  # None = leave unchanged; "" = clear
    model: str,
    parameters: dict[str, object] | None = None,
    system_prompt: str | None = None,
    timeout_ms: int = 30000,
    retries: int = 3,
    is_default: bool = False,
    is_active: bool = True,
) -> dict[str, object] | None:
    """Update a provider. Returns None if not found.

    api_key=None leaves the existing key unchanged.
    api_key="" clears the key.
    api_key="sk-..." sets a new key.
    """
    now = datetime.now(tz=UTC).isoformat()
    if is_default:
        await db.execute(
            "UPDATE ai_providers SET is_default = 0, updated_at = ? WHERE id != ?",
            (now, provider_id),
        )
    if api_key is None:
        # Leave the existing key untouched
        cursor = await db.execute(
            "UPDATE ai_providers SET name=?, provider_type=?, base_url=?, "
            "model=?, parameters=?, system_prompt=?, timeout_ms=?, retries=?, "
            "is_default=?, is_active=?, updated_at=? WHERE id=?",
            (
                name, provider_type, base_url, model,
                json.dumps(parameters or {}), system_prompt, timeout_ms, retries,
                int(is_default), int(is_active), now, provider_id,
            ),
        )
    else:
        cursor = await db.execute(
            "UPDATE ai_providers SET name=?, provider_type=?, base_url=?, api_key=?, "
            "model=?, parameters=?, system_prompt=?, timeout_ms=?, retries=?, "
            "is_default=?, is_active=?, updated_at=? WHERE id=?",
            (
                name, provider_type, base_url, api_key or None, model,
                json.dumps(parameters or {}), system_prompt, timeout_ms, retries,
                int(is_default), int(is_active), now, provider_id,
            ),
        )
    if cursor.rowcount == 0:
        return None
    await db.commit()
    return await get_provider(db, provider_id)


async def delete_provider(
    db: DatabasePort,
    provider_id: str,
) -> bool:
    """Delete a provider. Returns False if not found or is_default."""
    row = await (await db.execute(
        "SELECT is_default FROM ai_providers WHERE id = ?", (provider_id,)
    )).fetchone()
    if row is None or row[0]:
        return False
    await db.execute("DELETE FROM ai_providers WHERE id = ?", (provider_id,))
    await db.commit()
    return True


async def set_default_provider(
    db: DatabasePort,
    provider_id: str,
) -> dict[str, object] | None:
    """Set a provider as the default. Returns None if not found."""
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE ai_providers SET is_default = 0, updated_at = ?",
        (now,),
    )
    cursor = await db.execute(
        "UPDATE ai_providers SET is_default = 1, updated_at = ? WHERE id = ?",
        (now, provider_id),
    )
    if cursor.rowcount == 0:
        await db.commit()
        return None
    await db.commit()
    return await get_provider(db, provider_id)


async def get_default_provider(
    db: DatabasePort,
) -> dict[str, object] | None:
    """Get the default provider, or None if none set."""
    row = await (await db.execute(
        f"{_SELECT} WHERE is_default = 1 AND is_active = 1 LIMIT 1"
    )).fetchone()
    return _row_to_provider(row) if row else None


async def _get_provider_with_key(
    db: DatabasePort,
    provider_id: str,
) -> dict[str, object] | None:
    """Fetch provider including api_key — for internal client creation only."""
    row = await (await db.execute(f"{_SELECT} WHERE id = ?", (provider_id,))).fetchone()
    return _row_to_provider_with_key(row) if row else None


async def _get_default_provider_with_key(
    db: DatabasePort,
) -> dict[str, object] | None:
    """Fetch default provider including api_key — for internal client creation only."""
    row = await (await db.execute(
        f"{_SELECT} WHERE is_default = 1 AND is_active = 1 LIMIT 1"
    )).fetchone()
    return _row_to_provider_with_key(row) if row else None


async def test_provider(
    db: DatabasePort,
    provider_id: str,
) -> ProviderTestResult:
    """Test a provider's connection. Returns ProviderTestResult."""
    provider = await _get_provider_with_key(db, provider_id)
    if provider is None:
        return ProviderTestResult(ok=False, error="Provider not found")
    client = create_ai_client(provider)
    return await client.test_connection()


async def ask_question(
    db: DatabasePort,
    *,
    set_id: str,
    question: str,
    user_id: str,
    provider_id: str | None = None,
) -> dict[str, object]:
    """Ask a question about a Set. Stores conversation and usage log.

    Returns a conversation dict.
    """
    # 1. Resolve provider (with key for client auth)
    if provider_id:
        provider = await _get_provider_with_key(db, provider_id)
    else:
        provider = await _get_default_provider_with_key(db)

    if provider is None:
        msg = "No AI provider configured. Ask an admin to add a provider."
        raise ValueError(msg)

    # 2. Build set context
    context = await build_set_context(db, set_id)

    # 3. Build messages
    system_prompt = str(provider.get("system_prompt") or "")
    if system_prompt:
        system_content = f"{system_prompt}\n\nContext:\n{context}"
    else:
        system_content = (
            "You are an AI assistant helping users understand their architecture models. "
            "Answer questions based on the provided Set context.\n\nContext:\n" + context
        )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]

    # 4. Call LLM
    client = create_ai_client(provider)
    t0 = time.monotonic()
    answer, tokens_in, tokens_out = await client.chat(messages)
    duration_ms = int((time.monotonic() - t0) * 1000)

    # 5. Store conversation
    conv_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    model_used = str(provider["model"])
    context_summary = context[:200] + "..." if len(context) > 200 else context  # noqa: PLR2004

    await db.execute(
        "INSERT INTO ai_conversations "
        "(id, set_id, user_id, question, answer, context_summary, model_used, "
        "provider_id, tokens_in, tokens_out, duration_ms, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            conv_id, set_id, user_id, question, answer, context_summary,
            model_used, str(provider["id"]), tokens_in, tokens_out, duration_ms, now,
        ),
    )

    # 6. Log usage
    await db.execute(
        "INSERT INTO ai_usage_log "
        "(provider_id, user_id, endpoint, model, tokens_in, tokens_out, duration_ms, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(provider["id"]), user_id, "ask", model_used,
            tokens_in, tokens_out, duration_ms, "success", now,
        ),
    )
    await db.commit()

    return {
        "id": conv_id,
        "set_id": set_id,
        "question": question,
        "answer": answer,
        "model_used": model_used,
        "provider_id": str(provider["id"]),
        "provider_name": str(provider["name"]),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "duration_ms": duration_ms,
        "created_at": now,
    }


async def get_conversations(
    db: DatabasePort,
    *,
    set_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Get conversation history for a Set, newest first."""
    cursor = await db.execute(
        "SELECT id, set_id, user_id, question, answer, model_used, provider_id, "
        "tokens_in, tokens_out, duration_ms, created_at "
        "FROM ai_conversations WHERE set_id = ? "
        "ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (set_id, limit, offset),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "set_id": r[1],
            "user_id": r[2],
            "question": r[3],
            "answer": r[4],
            "model_used": r[5],
            "provider_id": r[6],
            "tokens_in": r[7],
            "tokens_out": r[8],
            "duration_ms": r[9],
            "created_at": r[10],
        }
        for r in rows
    ]


async def log_usage(
    db: DatabasePort,
    *,
    provider_id: str,
    user_id: str,
    endpoint: str,
    model: str,
    tokens_in: int | None,
    tokens_out: int | None,
    duration_ms: int,
    status: str,
    error: str | None = None,
) -> None:
    """Log an AI usage event."""
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO ai_usage_log "
        "(provider_id, user_id, endpoint, model, tokens_in, tokens_out, duration_ms, status, error, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (provider_id, user_id, endpoint, model, tokens_in, tokens_out, duration_ms, status, error, now),
    )
    await db.commit()
