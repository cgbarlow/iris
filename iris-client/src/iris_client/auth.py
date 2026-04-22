"""Auth header helpers for iris-client.

Both JWTs (issued by `/api/auth/login`) and PATs (issued by
`/api/users/me/tokens`, ADR-127) travel in the same
`Authorization: Bearer <token>` header. The client does not need to
distinguish between them — the backend does so by inspecting the
`iris_pat_` prefix (SPEC-127-A).

A `None` token means anonymous — no header is sent; the backend
applies the anonymous rate-limit bucket and, where ADR-123 allows,
serves the request.
"""

from __future__ import annotations


def bearer_headers(token: str | None) -> dict[str, str]:
    """Return `{"Authorization": "Bearer ..."}` or an empty dict."""
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def looks_like_pat(token: str | None) -> bool:
    """Best-effort check — useful for telemetry only.

    The backend is the authoritative judge of token validity; this helper
    exists so callers that want to surface "you are using a PAT" vs "you
    are using a JWT" in UX can do so without parsing tokens.
    """
    return bool(token) and token.startswith("iris_pat_")  # type: ignore[union-attr]
