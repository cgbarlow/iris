"""OAuth 2.1 endpoints (ADR-164, SPEC-164-A).

- `/.well-known/oauth-authorization-server` — RFC 8414 metadata.
- `/oauth/register` — RFC 7591 DCR.
- `/oauth/token` — RFC 6749 code/refresh exchange (with PKCE).
- `/oauth/revoke` — RFC 7009 revocation.

The user-facing authorization endpoint at `/oauth/authorize` is served
by SvelteKit (consent screen). The frontend page calls two backend
helpers:
- `POST /api/oauth/authorize/prepare` — validates the request and
  caches a server-side ConsentPayload keyed by request_id.
- `POST /api/oauth/authorize/decision` — processes Allow/Deny.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.oauth import service as oauth_service
from app.oauth.models import (
    AuthorizationServerMetadata,
    AuthorizeDecisionRequest,
    AuthorizeDecisionResponse,
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    ConsentPayload,
    TokenResponse,
)

router = APIRouter(tags=["oauth"])


def _issuer(request: Request) -> str:
    """Best-effort base URL — used for AS metadata + JWT aud."""
    return f"{request.url.scheme}://{request.url.netloc}"


@router.get(
    "/.well-known/oauth-authorization-server",
    response_model=AuthorizationServerMetadata,
)
async def authorization_server_metadata(
    request: Request,
) -> AuthorizationServerMetadata:
    """RFC 8414 — Authorization Server metadata.

    Anonymous-readable. iris-mcp's protected-resource metadata points
    here so MCP clients can discover the AS.
    """
    base = _issuer(request)
    return AuthorizationServerMetadata(
        issuer=base,
        authorization_endpoint=f"{base}/oauth/authorize",
        token_endpoint=f"{base}/oauth/token",
        registration_endpoint=f"{base}/oauth/register",
        revocation_endpoint=f"{base}/oauth/revoke",
        scopes_supported=["iris"],
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        code_challenge_methods_supported=["S256"],
        token_endpoint_auth_methods_supported=["none", "client_secret_basic"],
    )


@router.post(
    "/oauth/register",
    response_model=ClientRegistrationResponse,
    status_code=201,
)
async def register_client(
    body: ClientRegistrationRequest,
    request: Request,
) -> ClientRegistrationResponse:
    """RFC 7591 — Dynamic Client Registration.

    Open registration: any caller can self-register. User authorisation
    gates access (an unauthorised client_id with no granted code/
    refresh is useless).
    """
    db = request.app.state.db_manager.main_db
    result = await oauth_service.register_client(
        db,
        client_name=body.client_name,
        redirect_uris=[str(u) for u in body.redirect_uris],
        grant_types=list(body.grant_types),
        token_endpoint_auth_method=body.token_endpoint_auth_method,
    )
    return ClientRegistrationResponse(**result)


# ── Authorize: backend helpers behind /api/oauth/authorize/* ───────


@router.post(
    "/api/oauth/authorize/prepare",
    response_model=ConsentPayload,
)
async def prepare_authorize(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ConsentPayload:
    """Validate an incoming /oauth/authorize request and cache the
    consent payload server-side.

    The SvelteKit `/oauth/authorize` page reads the query params,
    POSTs them here (with the user's session bearer), and renders
    the consent screen using the returned `request_id`.

    400 on any validation failure. The frontend renders an error
    page rather than redirecting (we can't redirect-with-error
    until the redirect_uri is validated).
    """
    db = request.app.state.db_manager.main_db
    body = await request.json()

    # Required parameters per OAuth 2.1.
    client_id = body.get("client_id")
    redirect_uri = body.get("redirect_uri")
    response_type = body.get("response_type")
    code_challenge = body.get("code_challenge")
    code_challenge_method = body.get("code_challenge_method")
    scope = body.get("scope", "iris")
    state = body.get("state")

    if response_type != "code":
        raise HTTPException(status_code=400, detail="response_type must be 'code'")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri required")
    if not code_challenge:
        raise HTTPException(status_code=400, detail="code_challenge required (PKCE)")
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="code_challenge_method must be 'S256'")
    if scope and scope != "iris":
        raise HTTPException(status_code=400, detail="scope must be 'iris'")

    client = await oauth_service.get_client(db, client_id)
    if client is None:
        raise HTTPException(status_code=400, detail="unknown client_id")
    if redirect_uri not in client["redirect_uris"]:
        raise HTTPException(status_code=400, detail="redirect_uri not registered")

    payload = {
        "client_id": client_id,
        "client_name": client["client_name"],
        "user_id": current_user["id"],
        "username": current_user["username"],
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    request_id = oauth_service.cache_consent_payload(payload)
    return ConsentPayload(request_id=request_id, **payload)


@router.post(
    "/api/oauth/authorize/decision",
    response_model=AuthorizeDecisionResponse,
)
async def authorize_decision(
    body: AuthorizeDecisionRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AuthorizeDecisionResponse:
    """Process the user's Allow/Deny decision on the consent screen.

    Allow → mint an authorization code, redirect to
        `<redirect_uri>?code=...&state=...`
    Deny → redirect to `<redirect_uri>?error=access_denied&state=...`
    """
    db = request.app.state.db_manager.main_db
    payload = oauth_service.pop_consent_payload(body.request_id)
    if payload is None:
        raise HTTPException(status_code=400, detail="request_id expired or unknown")
    if payload["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="request belongs to another user")

    redirect_uri = payload["redirect_uri"]
    state = payload.get("state")

    if body.decision == "deny":
        qs = {"error": "access_denied"}
        if state:
            qs["state"] = state
        return AuthorizeDecisionResponse(
            redirect_to=f"{redirect_uri}?{urlencode(qs)}",
        )

    # decision == "allow"
    code = await oauth_service.create_authorization_code(
        db,
        client_id=payload["client_id"],
        user_id=payload["user_id"],
        redirect_uri=redirect_uri,
        code_challenge=payload["code_challenge"],
        code_challenge_method=payload["code_challenge_method"],
        scope=payload["scope"],
    )
    qs = {"code": code}
    if state:
        qs["state"] = state
    return AuthorizeDecisionResponse(
        redirect_to=f"{redirect_uri}?{urlencode(qs)}",
    )


# ── Token endpoint ─────────────────────────────────────────────────


@router.post("/oauth/token", response_model=TokenResponse)
async def token_endpoint(request: Request) -> TokenResponse:
    """RFC 6749 token endpoint with PKCE (RFC 7636).

    Supports two grant types:
    - `authorization_code`: exchange code+code_verifier for tokens.
    - `refresh_token`: rotate the refresh and issue a new access token.
    """
    db = request.app.state.db_manager.main_db
    config = request.app.state.config

    body_bytes = await request.body()
    # Accept both application/x-www-form-urlencoded (OAuth standard)
    # and application/json (lazy clients). Form is required by spec.
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        import json
        form = json.loads(body_bytes or b"{}")
    else:
        from urllib.parse import parse_qsl
        form = dict(parse_qsl(body_bytes.decode("ascii")))

    grant_type = form.get("grant_type")
    if grant_type == "authorization_code":
        code = form.get("code")
        client_id = form.get("client_id")
        redirect_uri = form.get("redirect_uri")
        code_verifier = form.get("code_verifier")
        if not (code and client_id and redirect_uri and code_verifier):
            raise HTTPException(status_code=400, detail={
                "error": "invalid_request",
                "error_description": (
                    "code, client_id, redirect_uri, code_verifier required"
                ),
            })

        # Validate client exists.
        client = await oauth_service.get_client(db, client_id)
        if client is None:
            raise HTTPException(status_code=400, detail={
                "error": "invalid_client",
            })

        result = await oauth_service.consume_authorization_code(
            db,
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
        if result is None:
            raise HTTPException(status_code=400, detail={
                "error": "invalid_grant",
            })

        access_token = await oauth_service.issue_access_token(
            db,
            user_id=result["user_id"],
            client_id=client_id,
            scope=result["scope"],
            config=config.auth,
        )
        refresh_token, _ = await oauth_service.create_refresh_token(
            db, client_id=client_id, user_id=result["user_id"],
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            scope=result["scope"],
        )

    if grant_type == "refresh_token":
        refresh_token = form.get("refresh_token")
        client_id = form.get("client_id")
        if not (refresh_token and client_id):
            raise HTTPException(status_code=400, detail={
                "error": "invalid_request",
            })

        result = await oauth_service.rotate_refresh_token(
            db, presented_token=refresh_token, client_id=client_id,
        )
        if result is None:
            raise HTTPException(status_code=400, detail={
                "error": "invalid_grant",
            })

        access_token = await oauth_service.issue_access_token(
            db,
            user_id=result["user_id"],
            client_id=client_id,
            scope=result["scope"],
            config=config.auth,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=result["refresh_token"],
            expires_in=3600,
            scope=result["scope"],
        )

    raise HTTPException(status_code=400, detail={
        "error": "unsupported_grant_type",
    })


# ── Revocation ─────────────────────────────────────────────────────


@router.post("/oauth/revoke", status_code=200)
async def revoke(request: Request) -> dict[str, str]:
    """RFC 7009 token revocation.

    Accepts form-encoded (spec) or JSON body. Always returns 200 per
    spec regardless of whether the token existed.
    """
    db = request.app.state.db_manager.main_db
    body_bytes = await request.body()
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        import json
        form = json.loads(body_bytes or b"{}")
    else:
        from urllib.parse import parse_qsl
        form = dict(parse_qsl(body_bytes.decode("ascii")))

    client_id = form.get("client_id")
    token = form.get("token")
    if not (client_id and token):
        # Per RFC 7009: best-effort response with 200, but log nothing.
        return {"status": "ok"}

    await oauth_service.revoke_refresh_token(db, token=token, client_id=client_id)
    return {"status": "ok"}
