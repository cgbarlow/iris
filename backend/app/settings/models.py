"""Settings request/response models."""

from __future__ import annotations

from pydantic import BaseModel


class SettingResponse(BaseModel):
    key: str
    value: str
    updated_at: str | None = None
    updated_by: str | None = None


class SettingUpdate(BaseModel):
    value: str
