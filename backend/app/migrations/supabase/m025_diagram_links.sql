-- Migration 025: Diagram links table for NavigationCell diagram references.

CREATE TABLE IF NOT EXISTS diagram_links (
    id               TEXT        PRIMARY KEY,
    source_diagram_id TEXT       NOT NULL REFERENCES diagrams(id) ON DELETE CASCADE,
    target_diagram_id TEXT       NOT NULL REFERENCES diagrams(id) ON DELETE CASCADE,
    link_type        TEXT        NOT NULL DEFAULT 'navigation',
    label            TEXT,
    created_by       TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_diagram_id, target_diagram_id, link_type)
);

CREATE INDEX IF NOT EXISTS idx_diagram_links_source ON diagram_links(source_diagram_id);
CREATE INDEX IF NOT EXISTS idx_diagram_links_target ON diagram_links(target_diagram_id);
