-- Migration 033: Add collections table and collection_id to sets/ai_conversations.

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ,
    created_by TEXT,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE,
    thumbnail_source TEXT,
    thumbnail_diagram_id TEXT,
    thumbnail_image BYTEA
);

CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_collections_name_active ON collections(name) WHERE is_deleted = FALSE;

ALTER TABLE sets ADD COLUMN IF NOT EXISTS collection_id TEXT REFERENCES collections(id);
CREATE INDEX IF NOT EXISTS idx_sets_collection ON sets(collection_id);

ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS collection_id TEXT REFERENCES collections(id);

-- Enable RLS (deny-all: backend postgres role bypasses, anon/authenticated denied)
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
