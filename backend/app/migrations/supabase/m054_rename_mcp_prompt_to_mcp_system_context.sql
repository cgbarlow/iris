-- Migration 054: rename `mcp_prompt` → `mcp_system_context` on
-- `collections` and `sets` (ADR-156, SPEC-156-A).
--
-- v5.10.0 (ADR-155) shipped the column as `mcp_prompt` and surfaced
-- its body via the MCP `prompts` channel (slash-command picker).
-- v5.11.0 (ADR-156) repositions it as a data passthrough field that
-- flows through get_set / get_collection MCP tool responses — no
-- slash command. Rename reflects the new purpose.
--
-- Idempotent — only renames if the old column exists and the new one
-- does not.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'collections' AND column_name = 'mcp_prompt'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'collections' AND column_name = 'mcp_system_context'
    ) THEN
        ALTER TABLE public.collections RENAME COLUMN mcp_prompt TO mcp_system_context;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sets' AND column_name = 'mcp_prompt'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sets' AND column_name = 'mcp_system_context'
    ) THEN
        ALTER TABLE public.sets RENAME COLUMN mcp_prompt TO mcp_system_context;
    END IF;
END $$;
