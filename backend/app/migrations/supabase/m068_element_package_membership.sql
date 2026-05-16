-- Migration 068: Element → package optional membership (ADR-184).
--
-- Adds nullable ``package_id`` column to ``elements`` plus an index.
-- Mirrors SQLite m064.
--
-- Idempotent.

ALTER TABLE public.elements
    ADD COLUMN IF NOT EXISTS package_id TEXT REFERENCES public.packages(id);

CREATE INDEX IF NOT EXISTS idx_elements_package
    ON public.elements(package_id);
