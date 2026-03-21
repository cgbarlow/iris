-- Migration 005: Full-text search support.
-- SQLite uses FTS5 virtual tables; PostgreSQL uses tsvector columns with
-- GIN indexes and auto-update triggers.
--
-- The search_vector columns and their GIN indexes are already created on
-- elements and diagrams in m002.  The FTS triggers are also defined there.
-- This migration is a no-op in PostgreSQL — it exists only for numbering
-- continuity so the runner applies migrations in order without gaps.

-- (intentional no-op: search infrastructure is part of m002 for PostgreSQL)
SELECT 1;
