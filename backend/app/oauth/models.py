"""Pydantic request / response models for the OAuth 2.1 endpoints
(ADR-164, SPEC-164-A)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# ── RFC 8414 Authorization Server Metadata ──────────────────────────


class AuthorizationServerMetadata(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str
    revocation_endpoint: str
    scopes_supported: list[str]
    response_types_supported: list[str]
    grant_types_supported: list[str]
    code_challenge_methods_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]


# ── RFC 7591 Dynamic Client Registration ────────────────────────────


class ClientRegistrationRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=255)
    redirect_uris: list[HttpUrl] = Field(min_length=1)
    grant_types: list[Literal["authorization_code", "refresh_token"]] = Field(
        default_factory=lambda: ["authorization_code", "refresh_token"],
    )
    token_endpoint_auth_method: Literal["none", "client_secret_basic"] = "none"


class ClientRegistrationResponse(BaseModel):
    client_id: str
    client_secret: str | None = None
    client_name: str
    redirect_uris: list[str]
    grant_types: list[str]
    token_endpoint_auth_method: str
    client_id_issued_at: int


# ── Authorize consent payload (server-rendered then POST decision) ──


class ConsentPayload(BaseModel):
    """Server-side cached representation of an in-progress authorize
    request, keyed by `request_id`. The frontend renders this on the
    /oauth/authorize consent screen and POSTs back to /decision."""

    request_id: str
    client_id: str
    client_name: str
    user_id: str
    username: str
    redirect_uri: str
    state: str | None = None
    scope: str = "iris"
    code_challenge: str
    code_challenge_method: Literal["S256"] = "S256"


class AuthorizeDecisionRequest(BaseModel):
    request_id: str
    decision: Literal["allow", "deny"]


class AuthorizeDecisionResponse(BaseModel):
    redirect_to: str


# ── Token endpoint ──────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int  # seconds
    scope: str = "iris"


# ── Revocation ──────────────────────────────────────────────────────


class RevokeRequest(BaseModel):
    token: str
    token_type_hint: Literal["refresh_token", "access_token"] = "refresh_token"
