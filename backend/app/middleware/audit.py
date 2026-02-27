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
    """Try to decode JWT claims from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):]
    try:
        return jwt.decode(
            token,
            request.app.state.config.auth.jwt_secret,
            algorithms=[request.app.state.config.auth.jwt_algorithm],
        )
    except Exception:
        return None


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return "unknown"


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

        try:
            audit_db = request.app.state.db_manager.audit_db
            await write_audit_entry(
                db=audit_db,
                user_id=user_id,
                username=user_id,
                action=action,
                target_type="http",
                target_id=request.url.path,
                detail={"status_code": response.status_code, "jti": jti},
                ip_address=ip_address,
            )
        except Exception:
            logger.exception("Failed to write audit entry for %s", action)

        return response
