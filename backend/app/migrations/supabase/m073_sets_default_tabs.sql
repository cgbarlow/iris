-- Migration 073: per-set tab defaults (ADR-204).
--
-- Mirrors SQLite m069. Adds two TEXT columns to ``sets`` so each set
-- chooses which tab is active by default on the Packages and Views
-- screens.
--
-- Values:
--   package_tab_default: 'relationships' | 'details'
--   view_tab_default:    'canvas' | 'relationships' | 'details'
--
-- Enums enforced at the application layer (Pydantic ``Literal``) rather
-- than SQL CHECK constraints — keeps SQLite and Supabase syntax
-- identical (Protocol §15).
--
-- Defaults are the new defaults, so existing rows inherit them with
-- no back-fill.
--
-- Idempotent.

ALTER TABLE public.sets
    ADD COLUMN IF NOT EXISTS package_tab_default TEXT NOT NULL DEFAULT 'relationships';

ALTER TABLE public.sets
    ADD COLUMN IF NOT EXISTS view_tab_default TEXT NOT NULL DEFAULT 'canvas';
