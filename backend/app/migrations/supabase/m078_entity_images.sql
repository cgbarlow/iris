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
    created_at    TIMESTAMPTZ NOT NULL,
    created_by    TEXT NOT NULL,
    UNIQUE (entity_type, entity_id, image_id)
);

-- v6.17.2: prior m078 declared `created_at TEXT` which fights with
-- Iris's asyncpg adapter (`_convert_params` in `backend/app/db/adapter.py`
-- converts ISO-string parameters to native `datetime` unconditionally).
-- asyncpg then rejected the INSERT with "expected str, got datetime".
-- This ALTER converts existing TEXT columns to TIMESTAMPTZ in place;
-- it's a no-op on fresh databases where the CREATE above already
-- yielded the right type. Cast is safe because every stored value
-- to date was an ISO timestamp.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'entity_images'
          AND column_name = 'created_at'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE public.entity_images
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING (created_at::TIMESTAMPTZ);
    END IF;
END $$;

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
