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
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scenia_timeline_settings_set_id ON scenia_timeline_settings(set_id);

CREATE TABLE IF NOT EXISTS scenia_versions (
    id TEXT PRIMARY KEY,
    set_id TEXT REFERENCES sets(id),
    version_number INTEGER NOT NULL,
    name TEXT,
    data TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
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
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_timeline_settings' AND policyname = 'scenia_timeline_settings_select') THEN
        CREATE POLICY "scenia_timeline_settings_select" ON scenia_timeline_settings FOR SELECT USING (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_versions' AND policyname = 'scenia_versions_select') THEN
        CREATE POLICY "scenia_versions_select" ON scenia_versions FOR SELECT USING (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_asset_categories' AND policyname = 'scenia_asset_categories_select') THEN
        CREATE POLICY "scenia_asset_categories_select" ON scenia_asset_categories FOR SELECT USING (TRUE);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_application_statuses' AND policyname = 'scenia_application_statuses_select') THEN
        CREATE POLICY "scenia_application_statuses_select" ON scenia_application_statuses FOR SELECT USING (TRUE);
    END IF;
END $$;

-- Only admins can modify
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_timeline_settings' AND policyname = 'scenia_timeline_settings_admin') THEN
        CREATE POLICY "scenia_timeline_settings_admin" ON scenia_timeline_settings FOR ALL USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_versions' AND policyname = 'scenia_versions_admin') THEN
        CREATE POLICY "scenia_versions_admin" ON scenia_versions FOR ALL USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_asset_categories' AND policyname = 'scenia_asset_categories_admin') THEN
        CREATE POLICY "scenia_asset_categories_admin" ON scenia_asset_categories FOR ALL USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'scenia_application_statuses' AND policyname = 'scenia_application_statuses_admin') THEN
        CREATE POLICY "scenia_application_statuses_admin" ON scenia_application_statuses FOR ALL USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        );
    END IF;
END $$;
