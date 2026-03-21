-- Migration 013: Set thumbnail columns.
-- In SQLite this added thumbnail_source, thumbnail_model_id, thumbnail_image
-- to the sets table.  In PostgreSQL the final column names
-- (thumbnail_source, thumbnail_diagram_id, thumbnail_image) are already
-- part of the sets table created in m002.
-- This migration is a no-op for numbering continuity.

-- (intentional no-op: thumbnail columns are part of sets table in m002)
SELECT 1;
