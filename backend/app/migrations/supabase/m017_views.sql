-- Migration 017: Views table for admin-configurable views (ADR-075).

CREATE TABLE IF NOT EXISTS views (
    id          TEXT        PRIMARY KEY,
    name        TEXT        NOT NULL UNIQUE,
    description TEXT,
    config      TEXT        NOT NULL DEFAULT '{}',
    is_default  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
