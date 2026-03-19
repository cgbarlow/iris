"""AI provider management and Set Q&A API endpoints (ADR-093)."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.ai.models import (
    ConversationResponse,
    ProviderCreate,
    ProviderResponse,
    ProviderTestResult,
    ProviderUpdate,
    QARequest,
    QAResponse,
)
from app.ai import service

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------------------------
# Admin: Provider CRUD
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[ProviderResponse]:
    """List all AI providers. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    providers = await service.list_providers(db)
    return [ProviderResponse(**p) for p in providers]


@router.post("/providers", response_model=ProviderResponse, status_code=201)
async def create_provider(
    body: ProviderCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ProviderResponse:
    """Create a new AI provider. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    provider = await service.create_provider(
        db,
        name=body.name,
        provider_type=body.provider_type,
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
        parameters=body.parameters.model_dump(exclude_none=True),
        system_prompt=body.system_prompt,
        timeout_ms=body.timeout_ms,
        retries=body.retries,
        is_default=body.is_default,
        is_active=body.is_active,
        created_by=current_user["id"],
    )
    return ProviderResponse(**provider)


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ProviderResponse:
    """Get an AI provider by ID. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    provider = await service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse(**provider)


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ProviderResponse:
    """Update an AI provider. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    provider = await service.update_provider(
        db,
        provider_id,
        name=body.name,
        provider_type=body.provider_type,
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
        parameters=body.parameters.model_dump(exclude_none=True),
        system_prompt=body.system_prompt,
        timeout_ms=body.timeout_ms,
        retries=body.retries,
        is_default=body.is_default,
        is_active=body.is_active,
    )
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse(**provider)


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete an AI provider. Admin only. Cannot delete the default provider."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    deleted = await service.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(
            status_code=400, detail="Provider not found or cannot delete default provider"
        )


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResult)
async def test_provider(
    provider_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ProviderTestResult:
    """Test an AI provider connection. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    return await service.test_provider(db, provider_id)


@router.post("/providers/{provider_id}/default", response_model=ProviderResponse)
async def set_default_provider(
    provider_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ProviderResponse:
    """Set a provider as the system default. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    provider = await service.set_default_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse(**provider)


@router.get("/usage")
async def get_usage_log(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    """Get AI usage log. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT id, provider_id, user_id, endpoint, model, tokens_in, tokens_out, "
        "duration_ms, status, error, created_at "
        "FROM ai_usage_log ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "provider_id": r[1],
            "user_id": r[2],
            "endpoint": r[3],
            "model": r[4],
            "tokens_in": r[5],
            "tokens_out": r[6],
            "duration_ms": r[7],
            "status": r[8],
            "error": r[9],
            "created_at": r[10],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# User: Set Q&A
# ---------------------------------------------------------------------------


@router.post("/sets/{set_id}/ask")
async def ask_question(
    set_id: str,
    body: QARequest,
    request: Request,
    stream: bool = Query(False),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> Any:
    """Ask a question about a Set. Returns QAResponse or SSE stream."""
    db = request.app.state.db_manager.main_db

    if stream:
        return await _ask_streaming(db, set_id=set_id, body=body, user_id=current_user["id"])

    try:
        result = await service.ask_question(
            db,
            set_id=set_id,
            question=body.question,
            user_id=current_user["id"],
            provider_id=body.provider_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc

    return QAResponse(
        answer=result["answer"],  # type: ignore[arg-type]
        model_used=result["model_used"],  # type: ignore[arg-type]
        provider_name=result["provider_name"],  # type: ignore[arg-type]
        tokens_in=result.get("tokens_in"),  # type: ignore[arg-type]
        tokens_out=result.get("tokens_out"),  # type: ignore[arg-type]
        duration_ms=result["duration_ms"],  # type: ignore[arg-type]
        conversation_id=result["id"],  # type: ignore[arg-type]
    )


async def _ask_streaming(
    db: Any,
    *,
    set_id: str,
    body: QARequest,
    user_id: str,
) -> StreamingResponse:
    """Return a StreamingResponse with SSE chunks from the LLM."""

    async def _generate() -> AsyncGenerator[str, None]:
        try:
            # Resolve provider
            if body.provider_id:
                provider = await service._get_provider_with_key(db, body.provider_id)
            else:
                provider = await service._get_default_provider_with_key(db)

            if provider is None:
                yield "data: " + json.dumps({"error": "No AI provider configured"}) + "\n\n"
                return

            context = await service.build_context(db, set_id)
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
                {"role": "user", "content": body.question},
            ]

            from app.ai.client import create_ai_client
            client = create_ai_client(provider)
            t0 = time.monotonic()
            full_answer: list[str] = []

            async for chunk in client.chat_stream(messages):
                full_answer.append(chunk)
                yield "data: " + json.dumps({"chunk": chunk}) + "\n\n"

            duration_ms = int((time.monotonic() - t0) * 1000)
            answer = "".join(full_answer)
            conv_id = str(uuid.uuid4())
            now = datetime.now(tz=UTC).isoformat()
            model_used = str(provider["model"])
            context_summary = context[:200] + "..." if len(context) > 200 else context  # noqa: PLR2004

            await db.execute(
                "INSERT INTO ai_conversations "
                "(id, set_id, user_id, question, answer, context_summary, model_used, "
                "provider_id, duration_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (conv_id, set_id, user_id, body.question, answer, context_summary,
                 model_used, str(provider["id"]), duration_ms, now),
            )
            await db.execute(
                "INSERT INTO ai_usage_log "
                "(provider_id, user_id, endpoint, model, duration_ms, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(provider["id"]), user_id, "ask_stream", model_used, duration_ms, "success", now),
            )
            await db.commit()

            yield "data: " + json.dumps({
                "done": True,
                "conversation_id": conv_id,
                "duration_ms": duration_ms,
                "model_used": model_used,
            }) + "\n\n"

        except Exception as exc:  # noqa: BLE001
            yield "data: " + json.dumps({"error": str(exc)}) + "\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sets/{set_id}/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    set_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[ConversationResponse]:
    """Get conversation history for a Set."""
    db = request.app.state.db_manager.main_db
    convs = await service.get_conversations(db, set_id=set_id, limit=limit, offset=offset)
    return [ConversationResponse(**c) for c in convs]
