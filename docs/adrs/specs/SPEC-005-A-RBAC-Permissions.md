# SPEC-005-A: RBAC Permission Matrix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-005-A |
| **ADR Reference** | [ADR-005: RBAC Design](../ADR-005-RBAC-Design.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the detailed RBAC permission matrix, schema design, and implementation guidance for Iris's four-role access control model.

---

## Roles

| Role ID | Display Name | Description | Default Count |
|---------|-------------|-------------|---------------|
| `admin` | Admin | System administration, user management, destructive operations | 1 (created on first run) |
| `architect` | Architect | Create and edit entities, models, relationships, versioning | 0 |
| `reviewer` | Reviewer | View, comment, approve/reject changes | 0 |
| `viewer` | Viewer | Browse-only access to published models | 0 |

---

## Permission Matrix

### Entity Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `entity.create` | Y | Y | | |
| `entity.read` | Y | Y | Y | Y |
| `entity.update` | Y | Y | | |
| `entity.delete` | Y | | | |

### Model Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `model.create` | Y | Y | | |
| `model.read` | Y | Y | Y | Y |
| `model.update` | Y | Y | | |
| `model.delete` | Y | | | |

### Relationship Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `relationship.create` | Y | Y | | |
| `relationship.read` | Y | Y | Y | Y |
| `relationship.delete` | Y | Y | | |

### Version Control Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `version.create` | Y | Y | | |
| `version.read` | Y | Y | Y | Y |
| `version.rollback` | Y | | | |

### Collaboration Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `comment.create` | Y | Y | Y | |
| `comment.read` | Y | Y | Y | Y |
| `comment.delete` | Y | Y | Y | |
| `comment.delete_any` | Y | | | |
| `bookmark.manage` | Y | Y | Y | Y |
| `search.execute` | Y | Y | Y | Y |

### User Management Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `user.create` | Y | | | |
| `user.read` | Y | Y | Y | Y |
| `user.update` | Y | | | |
| `user.delete` | Y | | | |
| `user.assign_role` | Y | | | |

### System Permissions

| Permission | Admin | Architect | Reviewer | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| `audit.read` | Y | | | |
| `system.configure` | Y | | | |

---

## Schema

### Tables

```sql
CREATE TABLE roles (
    id TEXT PRIMARY KEY,           -- 'admin', 'architect', 'reviewer', 'viewer'
    name TEXT NOT NULL,            -- Display name
    description TEXT NOT NULL,     -- Role description
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE role_permissions (
    role_id TEXT NOT NULL REFERENCES roles(id),
    permission TEXT NOT NULL,      -- e.g. 'entity.create'
    PRIMARY KEY (role_id, permission)
);

-- Users table includes role assignment
-- (defined in SPEC-005-B alongside auth fields)
```

### Seed Data

On database initialisation, the following roles and permissions are seeded:

```sql
INSERT INTO roles (id, name, description) VALUES
    ('admin', 'Admin', 'System administration, user management, all operations'),
    ('architect', 'Architect', 'Create and edit entities, models, relationships'),
    ('reviewer', 'Reviewer', 'View, comment, approve/reject changes'),
    ('viewer', 'Viewer', 'Browse-only access to published models');

-- Admin permissions (all 26 permissions)
INSERT INTO role_permissions (role_id, permission) VALUES
    ('admin', 'entity.create'), ('admin', 'entity.read'),
    ('admin', 'entity.update'), ('admin', 'entity.delete'),
    ('admin', 'model.create'), ('admin', 'model.read'),
    ('admin', 'model.update'), ('admin', 'model.delete'),
    ('admin', 'relationship.create'), ('admin', 'relationship.read'),
    ('admin', 'relationship.delete'),
    ('admin', 'version.create'), ('admin', 'version.read'),
    ('admin', 'version.rollback'),
    ('admin', 'comment.create'), ('admin', 'comment.read'),
    ('admin', 'comment.delete'), ('admin', 'comment.delete_any'),
    ('admin', 'bookmark.manage'), ('admin', 'search.execute'),
    ('admin', 'user.create'), ('admin', 'user.read'),
    ('admin', 'user.update'), ('admin', 'user.delete'),
    ('admin', 'user.assign_role'),
    ('admin', 'audit.read'), ('admin', 'system.configure');

-- Architect permissions (15 permissions)
INSERT INTO role_permissions (role_id, permission) VALUES
    ('architect', 'entity.create'), ('architect', 'entity.read'),
    ('architect', 'entity.update'),
    ('architect', 'model.create'), ('architect', 'model.read'),
    ('architect', 'model.update'),
    ('architect', 'relationship.create'), ('architect', 'relationship.read'),
    ('architect', 'relationship.delete'),
    ('architect', 'version.create'), ('architect', 'version.read'),
    ('architect', 'comment.create'), ('architect', 'comment.read'),
    ('architect', 'comment.delete'),
    ('architect', 'bookmark.manage'), ('architect', 'search.execute'),
    ('architect', 'user.read');

-- Reviewer permissions (8 permissions)
INSERT INTO role_permissions (role_id, permission) VALUES
    ('reviewer', 'entity.read'),
    ('reviewer', 'model.read'),
    ('reviewer', 'relationship.read'),
    ('reviewer', 'version.read'),
    ('reviewer', 'comment.create'), ('reviewer', 'comment.read'),
    ('reviewer', 'comment.delete'),
    ('reviewer', 'bookmark.manage'), ('reviewer', 'search.execute'),
    ('reviewer', 'user.read');

-- Viewer permissions (6 permissions)
INSERT INTO role_permissions (role_id, permission) VALUES
    ('viewer', 'entity.read'),
    ('viewer', 'model.read'),
    ('viewer', 'relationship.read'),
    ('viewer', 'version.read'),
    ('viewer', 'comment.read'),
    ('viewer', 'bookmark.manage'), ('viewer', 'search.execute'),
    ('viewer', 'user.read');
```

---

## Implementation Notes

### Permission Checking

```python
# FastAPI dependency for permission checking
async def require_permission(permission: str):
    async def check(current_user: User = Depends(get_current_user)):
        user_permissions = await get_permissions_for_role(current_user.role)
        if permission not in user_permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return check

# Usage in route
@router.post("/entities")
async def create_entity(
    entity: EntityCreate,
    user: User = Depends(require_permission("entity.create"))
):
    ...
```

### Permission Caching

Role-to-permission mappings are stable and rarely change. Cache them in memory on application startup and invalidate only when roles or permissions are modified by an Admin.

### Mode Mapping

| Role | Frontend Mode Access |
|------|---------------------|
| Admin | Edit Mode (Simple + Full View) + Browse Mode + Admin Panel |
| Architect | Edit Mode (Simple + Full View) + Browse Mode |
| Reviewer | Browse Mode + Comment Panel |
| Viewer | Browse Mode |

---

*This specification implements [ADR-005](../ADR-005-RBAC-Design.md).*
