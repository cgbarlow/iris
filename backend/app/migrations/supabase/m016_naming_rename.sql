-- Migration 016: Naming rename (entities→elements, models→diagrams+packages).
-- Per ADR-071.
-- In PostgreSQL all tables are created with the final names in m002, so
-- no renames are needed.  This migration is a no-op for numbering continuity.

-- (intentional no-op: final table names are used from m002 onward)
SELECT 1;
