"""Pydantic request / response models for the MCP pairing flow."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreatePairingCodeRequest(BaseModel):
    """Optional body for `POST /api/auth/pairing-codes`."""

    client_hint: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Short freeform tag stored in the issued PAT's name "
            "(e.g. 'claude-desktop'). Helps users disambiguate their PATs "
            "on the management page. Optional."
        ),
    )


class PairingCodeResponse(BaseModel):
    """Returned from `POST /api/auth/pairing-codes`."""

    code: str
    expires_at: str  # ISO-8601 UTC


class ExchangedPATResponse(BaseModel):
    """Returned from `POST /api/auth/pairing-codes/{code}/exchange`.

    The plaintext PAT secret is returned exactly once. Subsequent
    exchange attempts for the same code return 410.
    """

    token: str
    prefix: str
    expires_at: str  # ISO-8601 UTC of the PAT's expiry
    mode: Literal["pairing_code"] = "pairing_code"
