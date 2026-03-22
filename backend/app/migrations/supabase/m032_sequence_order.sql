-- Migration 032: Add sequence_order column to diagrams and packages tables.

ALTER TABLE diagrams ADD COLUMN IF NOT EXISTS sequence_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS sequence_order INTEGER NOT NULL DEFAULT 0;

-- Backfill existing rows by creation order
WITH numbered AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn
    FROM diagrams
)
UPDATE diagrams SET sequence_order = numbered.rn
FROM numbered WHERE diagrams.id = numbered.id;

WITH numbered AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn
    FROM packages
)
UPDATE packages SET sequence_order = numbered.rn
FROM numbered WHERE packages.id = numbered.id;
