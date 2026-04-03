-- Migration 037: Make ai_conversations.set_id nullable for file-only AI context.
ALTER TABLE ai_conversations ALTER COLUMN set_id DROP NOT NULL;
