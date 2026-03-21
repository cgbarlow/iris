-- Migration 007 + 010 + 016: Diagram thumbnails table.
-- m007 originally created model_thumbnails with a single PK on model_id.
-- m010 added a theme column with composite PK (model_id, theme).
-- m016 renamed the table to diagram_thumbnails with FK to diagrams(id).
-- PostgreSQL creates the final schema directly.

CREATE TABLE IF NOT EXISTS diagram_thumbnails (
    diagram_id TEXT        NOT NULL REFERENCES diagrams(id),
    theme      TEXT        NOT NULL DEFAULT 'dark',
    thumbnail  BYTEA       NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (diagram_id, theme)
);
