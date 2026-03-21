-- Migration 001: Roles, role_permissions, users, password_history, refresh_tokens.
-- Per SPEC-005-A (RBAC) and SPEC-005-B (Auth/Sessions).

CREATE TABLE IF NOT EXISTS roles (
    id          TEXT        PRIMARY KEY,
    name        TEXT        NOT NULL,
    description TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id    TEXT NOT NULL REFERENCES roles(id),
    permission TEXT NOT NULL,
    PRIMARY KEY (role_id, permission)
);

CREATE TABLE IF NOT EXISTS users (
    id                  TEXT        PRIMARY KEY,
    username            TEXT        NOT NULL UNIQUE,
    password_hash       TEXT        NOT NULL,
    role                TEXT        NOT NULL DEFAULT 'viewer' REFERENCES roles(id),
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    failed_login_count  INTEGER     NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS password_history (
    user_id       TEXT        NOT NULL REFERENCES users(id),
    password_hash TEXT        NOT NULL,
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, changed_at)
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         TEXT        PRIMARY KEY,
    user_id    TEXT        NOT NULL REFERENCES users(id),
    family_id  TEXT        NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    used_at    TIMESTAMPTZ,
    revoked    BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user   ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON refresh_tokens(family_id);

-- Seed roles (required before any user creation — the profiles trigger references roles.id)
INSERT INTO roles (id, name, description) VALUES
    ('admin', 'Admin', 'System administration, user management, all operations'),
    ('architect', 'Architect', 'Create and edit entities, models, relationships'),
    ('reviewer', 'Reviewer', 'View, comment, approve/reject changes'),
    ('viewer', 'Viewer', 'Browse-only access to published models')
ON CONFLICT (id) DO NOTHING;

-- Seed role permissions (SPEC-005-A)
INSERT INTO role_permissions (role_id, permission) VALUES
    -- admin (28 permissions)
    ('admin', 'entity.create'), ('admin', 'entity.read'), ('admin', 'entity.update'), ('admin', 'entity.delete'),
    ('admin', 'model.create'), ('admin', 'model.read'), ('admin', 'model.update'), ('admin', 'model.delete'),
    ('admin', 'relationship.create'), ('admin', 'relationship.read'), ('admin', 'relationship.delete'),
    ('admin', 'version.create'), ('admin', 'version.read'), ('admin', 'version.rollback'),
    ('admin', 'comment.create'), ('admin', 'comment.read'), ('admin', 'comment.delete'), ('admin', 'comment.delete_any'),
    ('admin', 'bookmark.manage'), ('admin', 'search.execute'),
    ('admin', 'user.create'), ('admin', 'user.read'), ('admin', 'user.update'), ('admin', 'user.delete'), ('admin', 'user.assign_role'),
    ('admin', 'audit.read'), ('admin', 'system.configure'),
    -- architect (17 permissions)
    ('architect', 'entity.create'), ('architect', 'entity.read'), ('architect', 'entity.update'),
    ('architect', 'model.create'), ('architect', 'model.read'), ('architect', 'model.update'),
    ('architect', 'relationship.create'), ('architect', 'relationship.read'), ('architect', 'relationship.delete'),
    ('architect', 'version.create'), ('architect', 'version.read'),
    ('architect', 'comment.create'), ('architect', 'comment.read'), ('architect', 'comment.delete'),
    ('architect', 'bookmark.manage'), ('architect', 'search.execute'),
    ('architect', 'user.read'),
    -- reviewer (10 permissions)
    ('reviewer', 'entity.read'),
    ('reviewer', 'model.read'),
    ('reviewer', 'relationship.read'),
    ('reviewer', 'version.read'),
    ('reviewer', 'comment.create'), ('reviewer', 'comment.read'), ('reviewer', 'comment.delete'),
    ('reviewer', 'bookmark.manage'), ('reviewer', 'search.execute'),
    ('reviewer', 'user.read'),
    -- viewer (8 permissions)
    ('viewer', 'entity.read'),
    ('viewer', 'model.read'),
    ('viewer', 'relationship.read'),
    ('viewer', 'version.read'),
    ('viewer', 'comment.read'),
    ('viewer', 'bookmark.manage'), ('viewer', 'search.execute'),
    ('viewer', 'user.read')
ON CONFLICT (role_id, permission) DO NOTHING;
