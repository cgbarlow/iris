"""AI provider management and Set Q&A API endpoints (ADR-093)."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

log = logging.getLogger("app.ai")
# Fallback: env var IRIS_AI_DEBUG=1 (overridden by DB setting debug_ai)
_AI_DEBUG_ENV = os.environ.get("IRIS_AI_DEBUG", "0") == "1"


async def _is_ai_debug(db: object) -> bool:
    """Check if AI debug logging is enabled (DB setting or env var)."""
    if _AI_DEBUG_ENV:
        return True
    try:
        cursor = await db.execute(  # type: ignore[union-attr]
            "SELECT value FROM settings WHERE key = 'debug_ai'",
        )
        row = await cursor.fetchone()
        return row is not None and row[0] == "1"
    except Exception:  # noqa: BLE001
        return False

from app.auth.dependencies import get_current_user
from app.ai.models import (
    ApplyCreationRequest,
    ApplyCreationResponse,
    ConversationResponse,
    CreationPromptResponse,
    CreationPromptUpdate,
    ProviderCreate,
    ProviderResponse,
    ProviderTestResult,
    ProviderUpdate,
    MultiSetQARequest,
    QARequest,
    QAResponse,
)
from app.ai import service
from app.ai.creation import create_diagrams_from_ai

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
        import logging
        logging.getLogger("app.ai").exception("LLM provider error in ask_question")
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
            print(f"[AI_ASK] mode={body.mode} notation={body.notation} question={body.question[:100]}", flush=True)
            ai_debug = await _is_ai_debug(db)

            # Resolve provider
            if body.provider_id:
                provider = await service._get_provider_with_key(db, body.provider_id)
            else:
                provider = await service._get_default_provider_with_key(db)

            if provider is None:
                yield "data: " + json.dumps({"error": "No AI provider configured"}) + "\n\n"
                return

            from app.ai.retrieval import get_retrieval_strategy
            retrieval = await get_retrieval_strategy(db)
            context = await retrieval.retrieve_context(db, body.question, [set_id])

            if body.mode == "creation":
                from app.ai.creation import build_creation_system_prompt
                creation_prompt = await build_creation_system_prompt(
                    db,
                    notation=body.notation or "doview",
                    diagram_type=None,
                )
                system_content = f"{creation_prompt}\n\n## Set Context (background only)\n\nBelow is existing content in the user's Set. This is BACKGROUND REFERENCE ONLY. The user decides what the DoView is about — do NOT assume the DoView topic matches the Set content. If the user says they want a DoView about X, make it about X regardless of what is in the Set.\n\n{context}"
            else:
                system_prompt = str(provider.get("system_prompt") or "")
                if system_prompt:
                    system_content = f"{system_prompt}\n\nContext:\n{context}"
                else:
                    system_content = (
                        "You are an AI assistant helping users understand their architecture models. "
                        "Answer questions based on the provided Set context.\n\nContext:\n" + context
                    )

            if body.mode == "creation":
                messages: list[dict[str, str]] = [
                    {"role": "system", "content": system_content},
                    {"role": "assistant", "content": "Describe in a couple of lines or less what you want a DoView of."},
                ]
                if body.history:
                    messages.extend(body.history)
                messages.append({"role": "user", "content": body.question})
            else:
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": body.question},
                ]

            if ai_debug:
                log.info("[AI_DEBUG] mode=%s notation=%s set_id=%s", body.mode, body.notation, set_id)
                log.info("[AI_DEBUG] provider=%s model=%s", provider["name"], provider["model"])
                log.info("[AI_DEBUG] system_prompt length=%d chars", len(system_content))
                log.info("[AI_DEBUG] history turns=%d", len(body.history) if body.history else 0)
                log.info("[AI_DEBUG] messages count=%d", len(messages))
                for i, m in enumerate(messages):
                    role = m["role"]
                    content_preview = m["content"][:200].replace("\n", "\\n")
                    log.info("[AI_DEBUG] msg[%d] role=%s len=%d preview=%s", i, role, len(m["content"]), content_preview)
                log.info("[AI_DEBUG] --- streaming start ---")

            from app.ai.client import create_ai_client
            client = create_ai_client(provider)
            t0 = time.monotonic()
            full_answer: list[str] = []

            async for chunk in client.chat_stream(messages):
                full_answer.append(chunk)
                yield "data: " + json.dumps({"chunk": chunk}) + "\n\n"

            duration_ms = int((time.monotonic() - t0) * 1000)
            answer = "".join(full_answer)

            if ai_debug:
                log.info("[AI_DEBUG] --- streaming complete ---")
                log.info("[AI_DEBUG] duration=%dms answer_length=%d chars", duration_ms, len(answer))
                log.info("[AI_DEBUG] answer_preview=%s", answer[:500].replace("\n", "\\n"))
            conv_id = str(uuid.uuid4())
            now = datetime.now(tz=UTC).isoformat()
            model_used = str(provider["model"])
            context_summary = context[:200] + "..." if len(context) > 200 else context  # noqa: PLR2004

            await db.execute(
                "INSERT INTO ai_conversations "
                "(id, set_id, user_id, question, answer, context_summary, model_used, "
                "provider_id, duration_ms, created_at, mode, thread_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (conv_id, set_id, user_id, body.question, answer, context_summary,
                 model_used, str(provider["id"]), duration_ms, now,
                 body.mode or "discuss", body.thread_id),
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


# ---------------------------------------------------------------------------
# User: Multi-Set Q&A (ADR-102 Collections)
# ---------------------------------------------------------------------------


@router.post("/ask")
async def ask_multi_set(
    body: MultiSetQARequest,
    request: Request,
    stream: bool = Query(False),
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> Any:
    """Ask a question across multiple Sets. Returns QAResponse or SSE stream."""
    db = request.app.state.db_manager.main_db

    if stream:
        return await _ask_multi_set_streaming(
            db, set_ids=body.set_ids, collection_id=body.collection_id,
            body=body, user_id=current_user["id"],
        )

    try:
        result = await service.ask_multi_set_question(
            db,
            set_ids=body.set_ids,
            collection_id=body.collection_id,
            question=body.question,
            user_id=current_user["id"],
            provider_id=body.provider_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("app.ai").exception("LLM provider error in ask_multi_set")
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


async def _ask_multi_set_streaming(
    db: Any,
    *,
    set_ids: list[str],
    collection_id: str | None,
    body: MultiSetQARequest,
    user_id: str,
) -> StreamingResponse:
    """Return a StreamingResponse with SSE chunks for multi-set Q&A."""

    async def _generate() -> AsyncGenerator[str, None]:
        try:
            print(f"[AI_ASK_MULTI] mode={body.mode} sets={len(set_ids)} question={body.question[:100]}", flush=True)
            ai_debug = await _is_ai_debug(db)

            # Resolve provider
            if body.provider_id:
                provider = await service._get_provider_with_key(db, body.provider_id)
            else:
                provider = await service._get_default_provider_with_key(db)

            if provider is None:
                yield "data: " + json.dumps({"error": "No AI provider configured"}) + "\n\n"
                return

            from app.ai.retrieval import get_retrieval_strategy
            retrieval = await get_retrieval_strategy(db)
            context = await retrieval.retrieve_context(
                db, body.question, set_ids, package_ids=body.package_ids,
            )

            primary_set_id = set_ids[0]

            if body.mode == "creation":
                from app.ai.creation import build_creation_system_prompt
                creation_prompt = await build_creation_system_prompt(
                    db,
                    notation=body.notation or "doview",
                    diagram_type=None,
                )
                system_content = f"{creation_prompt}\n\n## Set Context (background only)\n\nBelow is existing content from the user's Sets. This is BACKGROUND REFERENCE ONLY. The user decides what the DoView is about — do NOT assume the DoView topic matches the Set content. If the user says they want a DoView about X, make it about X regardless of what is in the Sets.\n\n{context}"
            else:
                system_prompt = str(provider.get("system_prompt") or "")
                if system_prompt:
                    system_content = f"{system_prompt}\n\nContext:\n{context}"
                else:
                    system_content = (
                        "You are an AI assistant helping users understand their architecture models. "
                        "Answer questions based on the provided context from multiple Sets.\n\nContext:\n" + context
                    )

            if body.mode == "creation":
                messages: list[dict[str, str]] = [
                    {"role": "system", "content": system_content},
                    {"role": "assistant", "content": "Describe in a couple of lines or less what you want a DoView of."},
                ]
                if body.history:
                    messages.extend(body.history)
                messages.append({"role": "user", "content": body.question})
            else:
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": body.question},
                ]

            if ai_debug:
                log.info("[AI_DEBUG_MULTI] mode=%s sets=%s", body.mode, set_ids)
                log.info("[AI_DEBUG_MULTI] provider=%s model=%s", provider["name"], provider["model"])
                log.info("[AI_DEBUG_MULTI] system_prompt length=%d chars", len(system_content))

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
                "provider_id, duration_ms, created_at, mode, thread_id, collection_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (conv_id, primary_set_id, user_id, body.question, answer, context_summary,
                 model_used, str(provider["id"]), duration_ms, now,
                 body.mode or "discuss", body.thread_id, collection_id),
            )
            await db.execute(
                "INSERT INTO ai_usage_log "
                "(provider_id, user_id, endpoint, model, duration_ms, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(provider["id"]), user_id, "ask_multi_stream", model_used, duration_ms, "success", now),
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


# ---------------------------------------------------------------------------
# Admin: Creation Prompt CRUD
# ---------------------------------------------------------------------------


@router.get("/creation-prompts", response_model=list[CreationPromptResponse])
async def list_creation_prompts(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[CreationPromptResponse]:
    """List all AI diagram creation prompts. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT id, name, description, layer, notation, diagram_type, "
        "prompt_text, display_order, is_active, created_by, created_at, updated_at "
        "FROM ai_creation_prompts ORDER BY layer, display_order"
    )
    rows = await cursor.fetchall()
    return [
        CreationPromptResponse(
            id=r[0],
            name=r[1],
            description=r[2],
            layer=r[3],
            notation=r[4],
            diagram_type=r[5],
            prompt_text=r[6],
            display_order=r[7],
            is_active=bool(r[8]),
            created_by=r[9],
            created_at=r[10],
            updated_at=r[11],
        )
        for r in rows
    ]


@router.put("/creation-prompts/{prompt_id}", response_model=CreationPromptResponse)
async def update_creation_prompt(
    prompt_id: str,
    body: CreationPromptUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CreationPromptResponse:
    """Update an AI creation prompt. Admin only."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db

    cursor = await db.execute(
        "SELECT id FROM ai_creation_prompts WHERE id = ?", (prompt_id,)
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Creation prompt not found")

    updates: list[str] = []
    params: list[Any] = []
    if body.prompt_text is not None:
        updates.append("prompt_text = ?")
        params.append(body.prompt_text)
    if body.is_active is not None:
        updates.append("is_active = ?")
        params.append(body.is_active)
    updates.append("updated_at = ?")
    params.append(datetime.now(tz=UTC).isoformat())

    if len(updates) > 1:  # at least one real field besides updated_at
        await db.execute(
            f"UPDATE ai_creation_prompts SET {', '.join(updates)} WHERE id = ?",  # noqa: S608
            (*params, prompt_id),
        )
        await db.commit()

    cursor = await db.execute(
        "SELECT id, name, description, layer, notation, diagram_type, "
        "prompt_text, display_order, is_active, created_by, created_at, updated_at "
        "FROM ai_creation_prompts WHERE id = ?",
        (prompt_id,),
    )
    row = await cursor.fetchone()
    return CreationPromptResponse(
        id=row[0],
        name=row[1],
        description=row[2],
        layer=row[3],
        notation=row[4],
        diagram_type=row[5],
        prompt_text=row[6],
        display_order=row[7],
        is_active=bool(row[8]),
        created_by=row[9],
        created_at=row[10],
        updated_at=row[11],
    )


# ---------------------------------------------------------------------------
# User: AI Diagram Creation Apply
# ---------------------------------------------------------------------------


@router.post(
    "/sets/{set_id}/create-diagram/apply",
    response_model=ApplyCreationResponse,
    status_code=201,
)
async def apply_diagram_creation(
    set_id: str,
    body: ApplyCreationRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ApplyCreationResponse:
    """Apply AI-generated diagram JSON to create diagrams in a Set."""
    db = request.app.state.db_manager.main_db

    # Verify set exists
    cursor = await db.execute("SELECT 1 FROM sets WHERE id = ?", (set_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Set not found")

    ai_debug = await _is_ai_debug(db)

    # Parse the AI JSON string
    try:
        ai_json = json.loads(body.diagrams_json)
    except (json.JSONDecodeError, ValueError) as exc:
        if ai_debug:
            log.error("[AI_DEBUG] apply: invalid JSON: %s", str(exc)[:200])
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc

    if ai_debug:
        diagram_count = len(ai_json.get("diagrams", []))
        log.info("[AI_DEBUG] apply: set_id=%s package_id=%s diagrams=%d json_len=%d",
                 set_id, body.package_id, diagram_count, len(body.diagrams_json))

    # Create diagrams
    try:
        diagram_ids = await create_diagrams_from_ai(
            db, set_id, ai_json, current_user["id"],
            package_id=body.package_id,
        )
    except (KeyError, ValueError) as exc:
        if ai_debug:
            log.error("[AI_DEBUG] apply: creation failed: %s", str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if ai_debug:
        log.info("[AI_DEBUG] apply: created %d diagrams, ids=%s", len(diagram_ids), diagram_ids)

    return ApplyCreationResponse(
        diagram_ids=diagram_ids,
        primary_diagram_id=diagram_ids[0] if diagram_ids else None,
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
