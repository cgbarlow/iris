-- Migration 034: Extensions registry table.
-- Per ADR-103 (Extensions Framework).

CREATE TABLE IF NOT EXISTS extensions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    version TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    installed_at TEXT NOT NULL,
    installed_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    config TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_extensions_name ON extensions(name);

-- Enable RLS
ALTER TABLE extensions ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read extensions
CREATE POLICY IF NOT EXISTS "extensions_select" ON extensions
    FOR SELECT USING (TRUE);

-- Only admins can modify extensions
CREATE POLICY IF NOT EXISTS "extensions_admin" ON extensions
    FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );
