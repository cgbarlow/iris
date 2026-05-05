-- Migration 046: Images (ADR-145, SPEC-145-A) — v5.4.0.
-- Backs paste-image-from-clipboard in the markdown editor.
-- BYTEA Postgres equivalent of the SQLite m045_images BLOB column.

CREATE TABLE IF NOT EXISTS images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mime TEXT NOT NULL,
  bytes BYTEA NOT NULL,
  size_bytes INTEGER NOT NULL,
  uploaded_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_images_uploaded_by ON images(uploaded_by);

ALTER TABLE images ENABLE ROW LEVEL SECURITY;

-- All-read for any authenticated user (images surface in markdown
-- viewers across the app), authenticated-write for upload. Mirrors the
-- DocRef RLS pattern (admin-write/all-read) but with authenticated-write
-- because regular users need to paste images.
DROP POLICY IF EXISTS images_select ON images;
CREATE POLICY images_select ON images
  FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS images_insert ON images;
CREATE POLICY images_insert ON images
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS images_delete ON images;
CREATE POLICY images_delete ON images
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
    OR uploaded_by = auth.uid()
  );
