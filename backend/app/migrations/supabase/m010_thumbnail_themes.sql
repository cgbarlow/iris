-- Migration 010: Thumbnail themes.
-- In SQLite, this migration recreated model_thumbnails to add a theme column
-- and composite PK.  In PostgreSQL the final schema is already created by
-- m007, so this migration is a no-op for numbering continuity.

-- (intentional no-op: theme column is part of diagram_thumbnails in m007)
SELECT 1;
