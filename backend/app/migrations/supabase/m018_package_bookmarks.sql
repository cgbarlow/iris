-- Migration 018: Extend bookmarks to support packages.
-- In PostgreSQL the final bookmarks schema (with both diagram_id and
-- package_id) is already created in m004.
-- This migration is a no-op for numbering continuity.

-- (intentional no-op: package_id column is part of bookmarks table in m004)
SELECT 1;
