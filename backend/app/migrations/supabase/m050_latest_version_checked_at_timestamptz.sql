-- Migration 050: Convert extensions.latest_version_checked_at from
-- TEXT to TIMESTAMPTZ on Postgres.
--
-- v5.5.8 (issue #55 follow-up). m048 declared the column as TEXT
-- (matching SQLite), but the rest of the extensions table uses
-- TIMESTAMPTZ for installed_at / updated_at. The asyncpg adapter
-- auto-converts ISO datetime strings to Python datetime objects;
-- when the resulting datetime is bound to a TEXT column,
-- asyncpg raises:
--
--   asyncpg.exceptions.DataError: invalid input for query argument
--   $2: datetime.datetime(...) (expected str, got datetime)
--
-- ...and the worker crashes mid-response, so /api/extensions/{id}/
-- check-update returned a 500 with no CORS headers.
--
-- Fix: align the column type with the rest of the table. ISO strings
-- cast cleanly to TIMESTAMPTZ, so the existing service code works
-- without changes.
--
-- Idempotent: ALTER … TYPE TIMESTAMPTZ USING …::timestamptz. If the
-- column is already TIMESTAMPTZ, the ALTER is a no-op (guarded by an
-- information_schema check).

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'extensions'
          AND column_name = 'latest_version_checked_at'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE extensions
            ALTER COLUMN latest_version_checked_at
            TYPE TIMESTAMPTZ
            USING latest_version_checked_at::timestamptz;
    END IF;
END
$$;
