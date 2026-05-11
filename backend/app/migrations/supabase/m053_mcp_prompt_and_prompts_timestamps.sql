-- Migration 053: scope MCP prompt column + v5.9.0 prompts.timestamps fix
-- (ADR-155, SPEC-155-A).
--
-- Two changes:
--
-- 1. Add a nullable `mcp_prompt TEXT` column to `collections` and `sets`.
--    Mirrors SQLite migration m049_mcp_prompt_column.py. Powers the
--    scope's MCP `prompts` picker entry under ADR-155 strict-split
--    semantics (does NOT auto-apply in Iris AI; that's still
--    system_prompt).
--
-- 2. Fix v5.9.0's `prompts.created_at` and `prompts.updated_at`
--    column types from `text` to `timestamptz`. The Supabase
--    adapter (backend/app/db/adapter.py:_convert_params) auto-
--    converts ISO datetime strings passed by service code into
--    native datetime objects before handing them to asyncpg.
--    asyncpg then rejects the datetime when the target column is
--    text. All other tables in Iris use `timestamptz` (m001, m007,
--    m025, m027, m046, etc.); the prompts table should too.
--
-- Idempotent. ADD COLUMN uses IF NOT EXISTS. ALTER COLUMN TYPE is
-- a no-op when types already match.

-- 1. mcp_prompt column on collections + sets.
ALTER TABLE collections
    ADD COLUMN IF NOT EXISTS mcp_prompt TEXT;

ALTER TABLE sets
    ADD COLUMN IF NOT EXISTS mcp_prompt TEXT;

-- 2. Convert v5.9.0 prompts.created_at / updated_at from text to
-- timestamptz. The `USING` clause parses the existing ISO strings
-- (if any rows already exist) into timestamptz values.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'prompts'
          AND column_name = 'created_at'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE public.prompts
            ALTER COLUMN created_at TYPE timestamptz
            USING created_at::timestamptz;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'prompts'
          AND column_name = 'updated_at'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE public.prompts
            ALTER COLUMN updated_at TYPE timestamptz
            USING updated_at::timestamptz;
    END IF;
END $$;
