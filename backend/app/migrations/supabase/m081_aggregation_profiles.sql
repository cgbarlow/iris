-- Migration 081: aggregation_profiles table (ADR-212).
--
-- Mirrors SQLite m076. JSONB for profile_data, BOOLEAN literals,
-- TIMESTAMPTZ for created_at/updated_at per Protocol §15 and the
-- feedback_supabase_created_at_type memory.
--
-- Idempotent via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS public.aggregation_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    set_id TEXT REFERENCES public.sets(id),
    is_global BOOLEAN NOT NULL DEFAULT FALSE,
    profile_data JSONB NOT NULL,
    is_default_for_set BOOLEAN NOT NULL DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK ((is_global = TRUE AND set_id IS NULL)
        OR (is_global = FALSE AND set_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_agg_profiles_set
    ON public.aggregation_profiles(set_id)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_agg_profiles_global
    ON public.aggregation_profiles(is_global)
    WHERE is_deleted = FALSE;
