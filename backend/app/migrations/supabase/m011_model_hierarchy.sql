-- Migration 011: Model hierarchy / parent_package_id.
-- In SQLite this added parent_model_id to the models table.
-- In PostgreSQL, packages and diagrams already have parent_package_id
-- in their final schemas (m002).  This migration ensures the index exists.

CREATE INDEX IF NOT EXISTS idx_packages_parent ON packages(parent_package_id);
CREATE INDEX IF NOT EXISTS idx_diagrams_parent  ON diagrams(parent_package_id);
