-- Migration 006: Settings table for admin-configurable parameters.

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT        PRIMARY KEY,
    value      TEXT        NOT NULL,
    updated_at TIMESTAMPTZ,
    updated_by TEXT
);
