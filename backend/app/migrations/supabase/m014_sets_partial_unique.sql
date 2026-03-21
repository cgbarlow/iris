-- Migration 014: Partial unique index on sets.name for active rows.
-- Per ADR-063 (Pagination, Set Uniqueness, Tree Explorer).
-- In PostgreSQL the partial unique index is already created in m002.
-- This migration is a no-op for numbering continuity.

-- (intentional no-op: idx_sets_name_active partial unique index is in m002)
SELECT 1;
