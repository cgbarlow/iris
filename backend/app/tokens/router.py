"""Personal Access Token management routes (ADR-127, SPEC-127-A).

Caller-scoped endpoints under `/api/users/me/tokens` — a logged-in user
lists/creates/revokes their own PATs. A PAT-authenticated caller can
manage that same user's PATs (PAT inherits user role).

Admin cross-user visibility is deferred per SPEC-127-A.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth.dependencies import get_current_user
from app.tokens import service as pat_service
from app.tokens.models import (
    TokenCreateRequest,
    TokenCreateResponse,
    TokenResponse,
)

router = APIRouter(tags=["Tokens"])


def _get_hasher(request: Request) -> Any:
    """Reuse the shared PAT hasher created at app startup.

    The application creates one PasswordHasher per process and attaches
    it to `app.state.pat_hasher` in the application factory.
    """
    return request.app.state.pat_hasher


@router.get(
    "/api/users/me/tokens",
    response_model=list[TokenResponse],
    summary="List the caller's Personal Access Tokens",
)
async def list_my_tokens(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[TokenResponse]:
    """Return all PATs belonging to the authenticated user.

    Never returns the token secret — only metadata (prefix, timestamps).
    """
    db = request.app.state.db_manager.main_db
    rows = await pat_service.list_tokens(db, current_user["id"])
    return [TokenResponse(**r) for r in rows]


@router.post(
    "/api/users/me/tokens",
    response_model=TokenCreateResponse,
    status_code=201,
    summary="Create a new Personal Access Token",
)
async def create_my_token(
    body: TokenCreateRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> TokenCreateResponse:
    """Create a PAT for the authenticated user.

    The plaintext `token` field is returned **only** on this response.
    After this, only the prefix and metadata are retrievable.
    """
    db = request.app.state.db_manager.main_db
    hasher = _get_hasher(request)
    record = await pat_service.create_token(
        db, current_user["id"], body.name, body.expires_at, hasher,
    )
    return TokenCreateResponse(**record)


@router.delete(
    "/api/users/me/tokens/{token_id}",
    status_code=204,
    response_class=Response,
    summary="Revoke a Personal Access Token",
)
async def revoke_my_token(
    token_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> Response:
    """Soft-revoke a PAT owned by the authenticated user.

    Idempotent — revoking an already-revoked token still returns 204.
    Returns 404 if the token does not exist or belongs to another user.
    """
    db = request.app.state.db_manager.main_db
    ok = await pat_service.revoke_token(db, current_user["id"], token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found")
    return Response(status_code=204)
