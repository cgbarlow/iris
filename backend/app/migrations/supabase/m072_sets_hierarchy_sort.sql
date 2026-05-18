-- Migration 072: per-set hierarchy sort preference (ADR-202).
--
-- Mirrors SQLite m068. Adds a ``hierarchy_sort`` column to ``sets``
-- so each set chooses how its diagram/package tree is ordered when
-- surfaced in the hierarchy views.
--
-- Values: 'manual' | 'alpha' | 'newest' | 'oldest'. Enum is enforced
-- at the application layer (Pydantic ``Literal``) rather than a SQL
-- CHECK constraint — keeps SQLite and Supabase syntax identical
-- (Protocol §15).
--
-- Default is 'manual' so existing sets keep their current ordering.
--
-- Idempotent.

ALTER TABLE public.sets
    ADD COLUMN IF NOT EXISTS hierarchy_sort TEXT NOT NULL DEFAULT 'manual';
