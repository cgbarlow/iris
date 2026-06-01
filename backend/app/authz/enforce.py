"""Write-scope enforcement helpers (ADR-237).

A user with no scope rows is *unscoped* (writes everywhere). Admins always
bypass. A *scoped* user may write only inside their whitelisted collections,
may never create or delete collections, and may not mutate global element
templates. Failures raise ``HTTPException(403)`` — consistent with
``require_permission`` (401 stays reserved for missing/invalid credentials).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from app.authz.collection_scope import load_scope

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

_FORBIDDEN_DETAIL = "Outside your collection write-scope"


def _is_exempt(user: dict[str, Any]) -> bool:
    """Admins bypass scoping entirely (they assign scopes themselves)."""
    return user.get("role") == "admin"


async def assert_write_allowed(
    db: DatabasePort, user: dict[str, Any], collection_id: str | None
) -> None:
    """Raise 403 if a scoped user is writing outside their scope.

    Admins and unscoped users (no scope rows) are always allowed. For a scoped
    user a ``collection_id`` of ``None`` — no owning collection, e.g. a global
    template or an un-grouped set — is treated as outside scope.
    """
    if _is_exempt(user):
        return
    scope = await load_scope(db, user["id"])
    if not scope:  # unscoped → write everywhere (pre-ADR-237 behaviour)
        return
    if collection_id is None or collection_id not in scope:
        raise HTTPException(status_code=403, detail=_FORBIDDEN_DETAIL)


async def assert_unscoped_or_admin(db: DatabasePort, user: dict[str, Any]) -> None:
    """Raise 403 for any scoped (non-admin) user.

    Guards operations a scoped user may never perform regardless of which
    collection is involved: creating or deleting a collection, and writing a
    server-wide (global) element template.
    """
    if _is_exempt(user):
        return
    scope = await load_scope(db, user["id"])
    if scope:
        raise HTTPException(status_code=403, detail=_FORBIDDEN_DETAIL)
