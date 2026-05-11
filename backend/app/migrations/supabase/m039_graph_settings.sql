-- Migration 039: Graph display settings per scope.

CREATE TABLE IF NOT EXISTS graph_settings (
    scope_type    TEXT        NOT NULL CHECK(scope_type IN ('global','collection','set')),
    scope_id      TEXT        NOT NULL,
    settings_json TEXT        NOT NULL,
    updated_at    TIMESTAMPTZ,
    updated_by    TEXT,
    PRIMARY KEY (scope_type, scope_id)
);

-- v5.8.1: enable RLS to match ADR-095 deny-all posture. PostgreSQL
-- treats ENABLE ROW LEVEL SECURITY as idempotent so re-running is safe.
ALTER TABLE graph_settings ENABLE ROW LEVEL SECURITY;
