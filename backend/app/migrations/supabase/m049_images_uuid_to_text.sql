-- Migration 049: Convert images.id and images.uploaded_by from UUID
-- to TEXT to match the SQLite schema and the service layer.
--
-- v5.5.1 (issue #46 item #4 root cause). The original m046_images.sql
-- declared id and uploaded_by as UUID, but Iris user IDs are TEXT and
-- the Python service generates `image_id = str(uuid.uuid4())`. With
-- the UUID column type, INSERT fails with "invalid input syntax for
-- type uuid" because asyncpg only auto-coerces ISO datetimes, not UUID
-- strings. So /api/images returned 500, the markdown editor's onpaste
-- catch (silent before v5.4.1; console.error after) swallowed the
-- failure, and users saw "ctrl-v does nothing".
--
-- Idempotent: ALTER … TYPE TEXT USING id::text. If the column is
-- already TEXT (e.g. on a fresh deploy that has only this migration
-- and m046 in correct shape), the ALTER is a no-op.

DO $$
BEGIN
    -- images.id: UUID → TEXT
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images' AND column_name = 'id' AND data_type = 'uuid'
    ) THEN
        ALTER TABLE images ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE images ALTER COLUMN id TYPE TEXT USING id::text;
    END IF;

    -- images.uploaded_by: UUID → TEXT
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'images' AND column_name = 'uploaded_by' AND data_type = 'uuid'
    ) THEN
        ALTER TABLE images ALTER COLUMN uploaded_by TYPE TEXT USING uploaded_by::text;
    END IF;
END
$$;
