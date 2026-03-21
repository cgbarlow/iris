-- Migration 015 + 016: Package relationships table.
-- m015 created model_relationships; m016 renamed it to package_relationships
-- with source_package_id / target_package_id columns.
-- PostgreSQL creates the final schema directly.

CREATE TABLE IF NOT EXISTS package_relationships (
    id                  TEXT        PRIMARY KEY,
    source_package_id   TEXT        NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    target_package_id   TEXT        NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    relationship_type   TEXT        NOT NULL,
    label               TEXT,
    description         TEXT,
    created_by          TEXT        NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_package_id, target_package_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_pkg_rel_source ON package_relationships(source_package_id);
CREATE INDEX IF NOT EXISTS idx_pkg_rel_target ON package_relationships(target_package_id);
