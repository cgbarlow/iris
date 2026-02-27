"""Migration 002: Entities, relationships, models and version tables.

Per SPEC-006-A (Entity Versioning) and SPEC-003-A (Entity Domain Model).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m002_entities_relationships_models"

UP_SQL = """
-- Entity identity table (SPEC-006-A)
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    current_version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_created_by ON entities(created_by);

-- Entity versions table (SPEC-006-A)
CREATE TABLE IF NOT EXISTS entity_versions (
    entity_id TEXT NOT NULL REFERENCES entities(id),
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    data TEXT NOT NULL,
    metadata TEXT,
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete')),
    change_summary TEXT,
    rollback_to INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (entity_id, version)
);

CREATE INDEX IF NOT EXISTS idx_entity_versions_created_at ON entity_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_entity_versions_created_by ON entity_versions(created_by);

-- Relationship identity table (SPEC-003-A)
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL REFERENCES entities(id),
    target_entity_id TEXT NOT NULL REFERENCES entities(id),
    relationship_type TEXT NOT NULL,
    current_version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_created_by ON relationships(created_by);

-- Relationship versions table (SPEC-003-A)
CREATE TABLE IF NOT EXISTS relationship_versions (
    relationship_id TEXT NOT NULL REFERENCES relationships(id),
    version INTEGER NOT NULL,
    label TEXT,
    description TEXT,
    data TEXT,
    metadata TEXT,
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete')),
    change_summary TEXT,
    rollback_to INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (relationship_id, version)
);

CREATE INDEX IF NOT EXISTS idx_rel_versions_created_at ON relationship_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_rel_versions_created_by ON relationship_versions(created_by);

-- Model identity table (SPEC-003-A)
CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,
    current_version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_models_type ON models(model_type);
CREATE INDEX IF NOT EXISTS idx_models_created_by ON models(created_by);

-- Model versions table (SPEC-003-A)
CREATE TABLE IF NOT EXISTS model_versions (
    model_id TEXT NOT NULL REFERENCES models(id),
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    data TEXT NOT NULL,
    metadata TEXT,
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete')),
    change_summary TEXT,
    rollback_to INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (model_id, version)
);

CREATE INDEX IF NOT EXISTS idx_model_versions_created_at ON model_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_model_versions_created_by ON model_versions(created_by);
"""


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    await db.executescript(UP_SQL)
    await db.commit()
