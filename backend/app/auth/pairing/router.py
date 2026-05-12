"""MCP pairing-code routes (ADR-160, SPEC-160-A).

- `POST /api/auth/pairing-codes` — authenticated; mints a one-shot code.
- `POST /api/auth/pairing-codes/{code}/exchange` — anonymous; exchanges
  the code for a freshly minted PAT.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.auth.pairing import service as pairing_service
from app.auth.pairing.models import (
    CreatePairingCodeRequest,
    ExchangedPATResponse,
    PairingCodeResponse,
)

router = APIRouter(prefix="/api/auth/pairing-codes", tags=["auth"])


@router.post(
    "",
    response_model=PairingCodeResponse,
    status_code=201,
    summary="Create a one-shot MCP pairing code",
)
async def create_pairing_code(
    request: Request,
    body: CreatePairingCodeRequest | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> PairingCodeResponse:
    """Mint a pairing code for the authenticated user (10-minute TTL).

    The user pastes the returned code into an MCP client (e.g. Claude
    Desktop) which calls `iris_authenticate(code)` to exchange it for a
    persistent PAT. See ADR-160.
    """
    db = request.app.state.db_manager.main_db
    result = await pairing_service.create_pairing_code(
        db,
        current_user["id"],
        client_hint=body.client_hint if body else None,
    )
    return PairingCodeResponse(**result)


@router.post(
    "/{code}/exchange",
    response_model=ExchangedPATResponse,
    summary="Exchange a pairing code for a Personal Access Token",
)
async def exchange_pairing_code(
    code: str,
    request: Request,
) -> ExchangedPATResponse:
    """Anonymous endpoint. One-shot exchange of a pairing code for a PAT.

    Returns 410 if the code is unknown, expired, or already exchanged.
    Successful exchange marks the code used and issues a fresh PAT
    with 90-day expiry, named per the original pairing-code request.
    """
    db = request.app.state.db_manager.main_db
    hasher = request.app.state.pat_hasher

    code_norm = code.strip().upper()
    result = await pairing_service.exchange_pairing_code(db, code_norm, hasher)
    if result is None:
        raise HTTPException(
            status_code=410,
            detail=(
                "Pairing code is unknown, expired, or already exchanged."
                " Generate a new one at /settings/mcp-pairing."
            ),
        )
    return ExchangedPATResponse(**result)
