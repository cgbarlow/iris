-- Migration 009 + 016: Diagram tags table.
-- m009 created model_tags; m016 renamed it to diagram_tags with diagram_id column.
-- PostgreSQL creates the final schema directly.

CREATE TABLE IF NOT EXISTS diagram_tags (
    diagram_id TEXT        NOT NULL REFERENCES diagrams(id),
    tag        TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT,
    PRIMARY KEY (diagram_id, tag)
);
