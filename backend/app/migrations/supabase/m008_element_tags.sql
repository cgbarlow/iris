-- Migration 008 + 016: Element tags table.
-- m008 created entity_tags; m016 renamed it to element_tags with element_id column.
-- PostgreSQL creates the final schema directly.

CREATE TABLE IF NOT EXISTS element_tags (
    element_id TEXT        NOT NULL REFERENCES elements(id),
    tag        TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT,
    PRIMARY KEY (element_id, tag)
);
