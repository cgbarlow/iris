-- Migration 036: Fix timestamp columns from TEXT to TIMESTAMPTZ.
-- The _convert_params adapter converts ISO strings to datetime objects for
-- asyncpg, which requires TIMESTAMPTZ columns (not TEXT) for datetime values.

-- Fix any underscore-formatted timestamps from legacy seed data before casting
UPDATE scenia_timeline_settings SET updated_at = REPLACE(updated_at::text, '_', 'T');
UPDATE scenia_versions SET created_at = REPLACE(created_at::text, '_', 'T');
UPDATE extensions SET installed_at = REPLACE(installed_at::text, '_', 'T');
UPDATE extensions SET updated_at = REPLACE(updated_at::text, '_', 'T');

ALTER TABLE scenia_timeline_settings
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::TIMESTAMPTZ;

ALTER TABLE scenia_versions
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::TIMESTAMPTZ;

ALTER TABLE extensions
    ALTER COLUMN installed_at TYPE TIMESTAMPTZ USING installed_at::TIMESTAMPTZ;

ALTER TABLE extensions
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::TIMESTAMPTZ;
