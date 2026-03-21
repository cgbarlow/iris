-- Migration 022: Add notation column to elements table (ADR-081).
-- In PostgreSQL the notation column is already on elements in m002.
-- This migration ensures idempotent addition in case the schema diverges.

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'elements' AND column_name = 'notation'
    ) THEN
        ALTER TABLE elements ADD COLUMN notation TEXT DEFAULT 'simple';
    END IF;
END $$;
