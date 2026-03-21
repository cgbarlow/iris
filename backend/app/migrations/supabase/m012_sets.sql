-- Migration 012: Sets table and set_id columns.
-- Per ADR-060 (Sets, Batch Operations).
-- In PostgreSQL the sets table, set_id columns on elements/diagrams, and
-- the Default set seed are already handled in m002.
-- This migration is a no-op for numbering continuity.

-- (intentional no-op: sets table and set_id columns are part of m002)
SELECT 1;
