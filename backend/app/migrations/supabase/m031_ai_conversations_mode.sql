-- m031: Add mode and thread_id columns to ai_conversations table.
-- These columns were added to SQLite after the initial Supabase migration (m026).

ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'discuss';
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS thread_id TEXT;
