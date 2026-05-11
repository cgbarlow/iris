-- Migration 052: Multiple named prompts per scope (ADR-154, SPEC-154-A).
--
-- Mirrors SQLite migration m048_named_prompts.py. Creates the
-- `prompts` table holding zero-or-more named prompts per Collection
-- or Set. Idempotent — every CREATE uses IF NOT EXISTS, every
-- POLICY is guarded with DO $$ ... $$.

CREATE TABLE IF NOT EXISTS public.prompts (
    id           text PRIMARY KEY,
    scope_type   text NOT NULL CHECK (scope_type IN ('collection','set')),
    scope_id     text NOT NULL,
    name         text NOT NULL,
    description  text NOT NULL,
    body         text NOT NULL,
    created_at   text NOT NULL,
    updated_at   text NOT NULL,
    created_by   text,
    UNIQUE (scope_type, scope_id, name)
);

CREATE INDEX IF NOT EXISTS idx_prompts_scope
    ON public.prompts(scope_type, scope_id);

ALTER TABLE public.prompts ENABLE ROW LEVEL SECURITY;

-- Anonymous read posture matches collections / sets / scope_system_prompts.
-- Authenticated writes only.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'prompts' AND policyname = 'prompts_anon_read'
    ) THEN
        CREATE POLICY prompts_anon_read ON public.prompts
            FOR SELECT USING (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'prompts' AND policyname = 'prompts_auth_insert'
    ) THEN
        CREATE POLICY prompts_auth_insert ON public.prompts
            FOR INSERT TO authenticated WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'prompts' AND policyname = 'prompts_auth_update'
    ) THEN
        CREATE POLICY prompts_auth_update ON public.prompts
            FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'prompts' AND policyname = 'prompts_auth_delete'
    ) THEN
        CREATE POLICY prompts_auth_delete ON public.prompts
            FOR DELETE TO authenticated USING (true);
    END IF;
END $$;
