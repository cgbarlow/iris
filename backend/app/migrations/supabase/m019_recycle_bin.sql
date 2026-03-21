-- Migration 019: Add deleted_group_id for recycle bin cascade grouping.
-- In PostgreSQL the deleted_group_id columns and their partial indexes are
-- already present on elements, diagrams, and packages in m002.
-- The updated change_type CHECK constraints (including 'restore') are also
-- already in m002.
-- This migration ensures idempotent column additions in case the schema
-- diverges, and is otherwise a no-op.

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'packages' AND column_name = 'deleted_group_id'
    ) THEN
        ALTER TABLE packages ADD COLUMN deleted_group_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_packages_deleted_group
            ON packages(deleted_group_id) WHERE deleted_group_id IS NOT NULL;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'diagrams' AND column_name = 'deleted_group_id'
    ) THEN
        ALTER TABLE diagrams ADD COLUMN deleted_group_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_diagrams_deleted_group
            ON diagrams(deleted_group_id) WHERE deleted_group_id IS NOT NULL;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'elements' AND column_name = 'deleted_group_id'
    ) THEN
        ALTER TABLE elements ADD COLUMN deleted_group_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_elements_deleted_group
            ON elements(deleted_group_id) WHERE deleted_group_id IS NOT NULL;
    END IF;
END $$;
