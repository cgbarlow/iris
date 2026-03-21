"""Audit middleware per SPEC-007-A — logs mutating requests to audit chain."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.audit.service import write_audit_entry

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response

logger = logging.getLogger(__name__)

_AUDITED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _decode_token(request: Request) -> dict[str, str] | None:
    """Try to decode JWT claims from Authorization header.

    SQLite mode: decodes with Iris JWT secret.
    Supabase mode: decodes with Supabase JWT secret (no aud verification).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):]
    config = request.app.state.config
    try:
        if config.db_backend == "supabase" and config.supabase:
            return jwt.decode(
                token,
                config.supabase.jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        return jwt.decode(
            token,
            config.auth.jwt_secret,
            algorithms=[config.auth.jwt_algorithm],
        )
    except Exception:
        return None


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return "unknown"


async def _resolve_username(request: Request, user_id: str) -> str:
    """Resolve user_id (GUID) to username.

    SQLite mode: queries users table.
    Supabase mode: queries profiles table (id is UUID, cast to text for comparison).
    """
    if user_id == "anonymous":
        return "anonymous"
    try:
        config = request.app.state.config
        main_db = request.app.state.db_manager.main_db
        if config.db_backend == "supabase":
            cursor = await main_db.execute(
                "SELECT username FROM profiles WHERE id::text = ?", (user_id,),
            )
        else:
            cursor = await main_db.execute(
                "SELECT username FROM users WHERE id = ?", (user_id,),
            )
        row = await cursor.fetchone()
        return row[0] if row else user_id
    except Exception:
        return user_id


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs mutating requests to the audit chain."""

    async def dispatch(
        self, request: Request, call_next: Callable[..., Response]
    ) -> Response:
        """Intercept mutating requests and write audit entries."""
        response: Response = await call_next(request)  # type: ignore[misc]

        if request.method not in _AUDITED_METHODS:
            return response

        action = f"{request.method} {request.url.path}"
        claims = _decode_token(request)
        user_id = claims.get("sub", "anonymous") if claims else "anonymous"
        jti = claims.get("jti") if claims else None
        ip_address = _get_client_ip(request)
        username = await _resolve_username(request, user_id)

        try:
            audit_db = request.app.state.db_manager.audit_db
            await write_audit_entry(
                db=audit_db,
                user_id=user_id,
                username=username,
                action=action,
                target_type="http",
                target_id=request.url.path,
                detail={"status_code": response.status_code, "jti": jti},
                ip_address=ip_address,
            )
        except Exception:
            logger.exception("Failed to write audit entry for %s", action)

        return response
