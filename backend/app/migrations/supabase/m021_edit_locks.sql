-- Migration 021: Edit locks table for pessimistic locking (ADR-080).

CREATE TABLE IF NOT EXISTS edit_locks (
    id             TEXT        PRIMARY KEY,
    target_type    TEXT        NOT NULL CHECK (target_type IN ('diagram', 'element', 'package')),
    target_id      TEXT        NOT NULL,
    user_id        TEXT        NOT NULL,
    username       TEXT        NOT NULL,
    acquired_at    TIMESTAMPTZ NOT NULL,
    expires_at     TIMESTAMPTZ NOT NULL,
    last_heartbeat TIMESTAMPTZ NOT NULL,
    UNIQUE (target_type, target_id)
);
