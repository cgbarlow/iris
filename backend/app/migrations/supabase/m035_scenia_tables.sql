-- Migration 035: Create Scenia-specific tables.
-- Per ADR-105 (Scenia Integration).

CREATE TABLE IF NOT EXISTS scenia_timeline_settings (
    id TEXT PRIMARY KEY,
    set_id TEXT REFERENCES sets(id),
    start_date TEXT,
    end_date TEXT,
    view_mode TEXT DEFAULT 'quarterly',
    zoom_level REAL DEFAULT 1.0,
    data TEXT DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scenia_timeline_settings_set_id ON scenia_timeline_settings(set_id);

CREATE TABLE IF NOT EXISTS scenia_versions (
    id TEXT PRIMARY KEY,
    set_id TEXT REFERENCES sets(id),
    version_number INTEGER NOT NULL,
    name TEXT,
    data TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scenia_versions_set_id ON scenia_versions(set_id);

CREATE TABLE IF NOT EXISTS scenia_asset_categories (
    id TEXT PRIMARY KEY,
    set_id TEXT REFERENCES sets(id),
    name TEXT NOT NULL,
    color TEXT,
    display_order INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_scenia_asset_categories_set_id ON scenia_asset_categories(set_id);

CREATE TABLE IF NOT EXISTS scenia_application_statuses (
    id TEXT PRIMARY KEY,
    set_id TEXT REFERENCES sets(id),
    name TEXT NOT NULL,
    color TEXT,
    display_order INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_scenia_application_statuses_set_id ON scenia_application_statuses(set_id);

-- Enable RLS
ALTER TABLE scenia_timeline_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenia_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenia_asset_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenia_application_statuses ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read
CREATE POLICY IF NOT EXISTS "scenia_timeline_settings_select" ON scenia_timeline_settings
    FOR SELECT USING (TRUE);

CREATE POLICY IF NOT EXISTS "scenia_versions_select" ON scenia_versions
    FOR SELECT USING (TRUE);

CREATE POLICY IF NOT EXISTS "scenia_asset_categories_select" ON scenia_asset_categories
    FOR SELECT USING (TRUE);

CREATE POLICY IF NOT EXISTS "scenia_application_statuses_select" ON scenia_application_statuses
    FOR SELECT USING (TRUE);

-- Only admins can modify
CREATE POLICY IF NOT EXISTS "scenia_timeline_settings_admin" ON scenia_timeline_settings
    FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY IF NOT EXISTS "scenia_versions_admin" ON scenia_versions
    FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY IF NOT EXISTS "scenia_asset_categories_admin" ON scenia_asset_categories
    FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY IF NOT EXISTS "scenia_application_statuses_admin" ON scenia_application_statuses
    FOR ALL USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );
