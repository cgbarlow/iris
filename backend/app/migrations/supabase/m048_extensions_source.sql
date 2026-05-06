-- Migration 048: Track extension source method, source URL, and the
-- latest known release.
--
-- v5.5.0 (issue #48). Mirrors SQLite migration m046_extensions_source.
-- Idempotent — uses IF NOT EXISTS so re-running on a partially-applied
-- DB is safe.

ALTER TABLE extensions
    ADD COLUMN IF NOT EXISTS source_method TEXT NOT NULL DEFAULT 'local';

ALTER TABLE extensions
    ADD COLUMN IF NOT EXISTS source_url TEXT;

ALTER TABLE extensions
    ADD COLUMN IF NOT EXISTS latest_version TEXT;

ALTER TABLE extensions
    ADD COLUMN IF NOT EXISTS latest_version_checked_at TEXT;
