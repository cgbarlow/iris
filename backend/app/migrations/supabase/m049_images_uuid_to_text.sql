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
-- Postgres refuses to ALTER a column type while a policy references
-- it, so we drop the images_delete policy (which references
-- uploaded_by) before the ALTER and recreate it with an explicit
-- ::text cast against auth.uid() afterward.
--
-- Idempotent: ALTER … TYPE TEXT USING …::text. If the column is
-- already TEXT (e.g. on a fresh deploy that has only this migration
-- and m046 in correct shape), the ALTER is a no-op.

DO $$
BEGIN
    -- Drop the policies that depend on uploaded_by so we can ALTER.
    -- DROP POLICY IF EXISTS is idempotent — safe if policies were
    -- never created.
    DROP POLICY IF EXISTS images_delete ON images;

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

-- Recreate the policy with TEXT-aware comparisons. `profiles.id` is
-- UUID so the inner check compares UUID-to-UUID; `uploaded_by` is now
-- TEXT so it compares against auth.uid()::text.
CREATE POLICY images_delete ON images
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
    OR uploaded_by = auth.uid()::text
  );
