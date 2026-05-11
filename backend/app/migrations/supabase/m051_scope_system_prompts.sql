-- Migration 051: Scope-level system prompts (ADR-150, SPEC-150-A).
--
-- Mirrors SQLite migration m047_scope_system_prompts.py. Adds a
-- nullable `system_prompt TEXT` column to `collections` and `sets`.
-- Composition is runtime; this migration only adds storage.
--
-- Idempotent — uses IF NOT EXISTS so re-running on a partially-applied
-- DB is safe.

ALTER TABLE collections
    ADD COLUMN IF NOT EXISTS system_prompt TEXT;

ALTER TABLE sets
    ADD COLUMN IF NOT EXISTS system_prompt TEXT;
