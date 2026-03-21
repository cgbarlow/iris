-- Migration 003: Audit log table.
-- Per SPEC-007-A (Audit Log Schema and Hash Chain Implementation).
-- In PostgreSQL (Supabase), the audit log lives in the same database
-- rather than a separate file as in the SQLite implementation.

CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL   PRIMARY KEY,
    timestamp     TIMESTAMPTZ NOT NULL,
    user_id       TEXT        NOT NULL,
    username      TEXT        NOT NULL,
    action        TEXT        NOT NULL,
    target_type   TEXT        NOT NULL,
    target_id     TEXT,
    detail        TEXT,
    ip_address    TEXT,
    session_id    TEXT,
    previous_hash TEXT        NOT NULL,
    entry_hash    TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id   ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action    ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_target    ON audit_log(target_type, target_id);
