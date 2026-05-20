-- Migration 077: per-set element_tab_default (ADR-208).
--
-- Mirrors SQLite m072. Adds a TEXT column to ``sets`` so each set
-- chooses which tab is active by default on the Elements screen.
--
-- Value: 'details' | 'diagrams' | 'relationships' | 'versions'.
-- Default 'relationships' per ADR-208.
--
-- Enum enforced at the application layer (Pydantic Literal) rather
-- than SQL CHECK constraints — keeps SQLite and Supabase syntax
-- identical (Protocol §15).
--
-- Idempotent.

ALTER TABLE public.sets
    ADD COLUMN IF NOT EXISTS element_tab_default TEXT NOT NULL DEFAULT 'relationships';
