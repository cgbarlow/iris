-- Migration 047: Extend bookmarks to support elements.
--
-- Mirrors the SQLite migration m038_element_bookmarks (the original
-- Supabase mirror was missed when the SQLite migration shipped — issue
-- #37 reopen surfaced as a 500 on /api/bookmarks because the
-- element_id column the bookmarks router selects didn't exist on
-- Postgres). Adds element_id alongside diagram_id and package_id, and
-- replaces the existing 2-way CHECK constraint with a 3-way one so a
-- bookmark can target any of the three.

ALTER TABLE bookmarks
    ADD COLUMN IF NOT EXISTS element_id TEXT REFERENCES elements(id);

CREATE INDEX IF NOT EXISTS idx_bookmarks_element ON bookmarks(element_id);

-- Replace the old (diagram_id XOR package_id) CHECK with a 3-way one.
-- The constraint name in m004 is auto-generated; drop by table-name
-- pattern so this is idempotent across deployments.
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'bookmarks'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%diagram_id%package_id%';
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE bookmarks DROP CONSTRAINT %I', constraint_name);
    END IF;
END
$$;

ALTER TABLE bookmarks ADD CONSTRAINT bookmarks_target_check CHECK (
    (diagram_id IS NOT NULL AND package_id IS NULL AND element_id IS NULL)
    OR (diagram_id IS NULL AND package_id IS NOT NULL AND element_id IS NULL)
    OR (diagram_id IS NULL AND package_id IS NULL AND element_id IS NOT NULL)
);

-- Add the per-user UNIQUE so an element can't be double-bookmarked.
ALTER TABLE bookmarks DROP CONSTRAINT IF EXISTS bookmarks_user_id_element_id_key;
ALTER TABLE bookmarks ADD CONSTRAINT bookmarks_user_id_element_id_key UNIQUE (user_id, element_id);
