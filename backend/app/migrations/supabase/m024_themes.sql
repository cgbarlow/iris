-- Migration 024: Themes table for visual theme system (ADR-084).

CREATE TABLE IF NOT EXISTS themes (
    id          TEXT        PRIMARY KEY,
    name        TEXT        NOT NULL UNIQUE,
    description TEXT,
    notation    TEXT        NOT NULL,
    config      TEXT        NOT NULL DEFAULT '{}',
    is_default  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
