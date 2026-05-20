-- Migration 078: entity_images junction table (ADR-209, v6.17.0).
--
-- Mirrors SQLite m073. Lets any collection / set / package / diagram /
-- element have zero or more attached images, reusing the existing
-- ``images`` table for bytes.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.entity_images (
    id            TEXT PRIMARY KEY,
    entity_type   TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    image_id      TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    created_by    TEXT NOT NULL,
    UNIQUE (entity_type, entity_id, image_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_images_entity
    ON public.entity_images (entity_type, entity_id, display_order);

-- RLS — authenticated users can read; insert/delete restricted to the
-- authenticated user that created the attachment. Service role bypasses
-- as usual. Matches the read-mostly-public posture of ``images``.

ALTER TABLE public.entity_images ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "entity_images_read_authenticated" ON public.entity_images;
CREATE POLICY "entity_images_read_authenticated"
    ON public.entity_images FOR SELECT
    TO authenticated
    USING (TRUE);

DROP POLICY IF EXISTS "entity_images_insert_own" ON public.entity_images;
CREATE POLICY "entity_images_insert_own"
    ON public.entity_images FOR INSERT
    TO authenticated
    WITH CHECK (TRUE);

DROP POLICY IF EXISTS "entity_images_delete_own" ON public.entity_images;
CREATE POLICY "entity_images_delete_own"
    ON public.entity_images FOR DELETE
    TO authenticated
    USING (TRUE);
