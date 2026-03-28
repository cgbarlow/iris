-- Migration 036: Fix Scenia timestamp columns from TEXT to TIMESTAMPTZ.
-- The _convert_params adapter converts ISO strings to datetime objects for
-- asyncpg, which requires TIMESTAMPTZ columns (not TEXT) for datetime values.

ALTER TABLE scenia_timeline_settings
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::TIMESTAMPTZ;

ALTER TABLE scenia_versions
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::TIMESTAMPTZ;
