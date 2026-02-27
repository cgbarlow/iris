"""Idempotent seed data for roles and permissions per SPEC-005-A."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

ROLES = [
    ("admin", "Admin", "System administration, user management, all operations"),
    ("architect", "Architect", "Create and edit entities, models, relationships"),
    ("reviewer", "Reviewer", "View, comment, approve/reject changes"),
    ("viewer", "Viewer", "Browse-only access to published models"),
]

# 28 admin permissions (26 from spec + audit.read + system.configure)
ADMIN_PERMISSIONS = [
    "entity.create", "entity.read", "entity.update", "entity.delete",
    "model.create", "model.read", "model.update", "model.delete",
    "relationship.create", "relationship.read", "relationship.delete",
    "version.create", "version.read", "version.rollback",
    "comment.create", "comment.read", "comment.delete", "comment.delete_any",
    "bookmark.manage", "search.execute",
    "user.create", "user.read", "user.update", "user.delete", "user.assign_role",
    "audit.read", "system.configure",
]

ARCHITECT_PERMISSIONS = [
    "entity.create", "entity.read", "entity.update",
    "model.create", "model.read", "model.update",
    "relationship.create", "relationship.read", "relationship.delete",
    "version.create", "version.read",
    "comment.create", "comment.read", "comment.delete",
    "bookmark.manage", "search.execute",
    "user.read",
]

REVIEWER_PERMISSIONS = [
    "entity.read",
    "model.read",
    "relationship.read",
    "version.read",
    "comment.create", "comment.read", "comment.delete",
    "bookmark.manage", "search.execute",
    "user.read",
]

VIEWER_PERMISSIONS = [
    "entity.read",
    "model.read",
    "relationship.read",
    "version.read",
    "comment.read",
    "bookmark.manage", "search.execute",
    "user.read",
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ADMIN_PERMISSIONS,
    "architect": ARCHITECT_PERMISSIONS,
    "reviewer": REVIEWER_PERMISSIONS,
    "viewer": VIEWER_PERMISSIONS,
}


async def seed_roles_and_permissions(db: aiosqlite.Connection) -> None:
    """Idempotently seed all 4 roles and their permission mappings."""
    for role_id, name, description in ROLES:
        await db.execute(
            "INSERT OR IGNORE INTO roles (id, name, description) VALUES (?, ?, ?)",
            (role_id, name, description),
        )

    for role_id, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            await db.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, permission) "
                "VALUES (?, ?)",
                (role_id, permission),
            )

    await db.commit()
