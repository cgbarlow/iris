"""Pydantic models for the audit service."""

from __future__ import annotations

from pydantic import BaseModel


class AuditEntry(BaseModel):
    """Represents a single audit log entry."""

    id: int
    timestamp: str
    user_id: str
    username: str
    action: str
    target_type: str
    target_id: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    session_id: str | None = None
    previous_hash: str
    entry_hash: str


class AuditVerifyResult(BaseModel):
    """Result of audit chain verification."""

    valid: bool
    entries_checked: int
    verified_at: str
