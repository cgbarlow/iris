-- Migration 026: AI provider registry and conversation tables (ADR-093).

CREATE TABLE IF NOT EXISTS ai_providers (
    id           TEXT        PRIMARY KEY,
    name         TEXT        NOT NULL UNIQUE,
    provider_type TEXT       NOT NULL,
    base_url     TEXT,
    api_key      TEXT,
    model        TEXT        NOT NULL,
    parameters   TEXT        NOT NULL DEFAULT '{}',
    system_prompt TEXT,
    timeout_ms   INTEGER     NOT NULL DEFAULT 30000,
    retries      INTEGER     NOT NULL DEFAULT 3,
    is_default   BOOLEAN     NOT NULL DEFAULT FALSE,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_by   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id              TEXT        PRIMARY KEY,
    set_id          TEXT        REFERENCES sets(id),
    user_id         TEXT        NOT NULL,
    question        TEXT        NOT NULL,
    answer          TEXT        NOT NULL,
    context_summary TEXT,
    model_used      TEXT        NOT NULL,
    provider_id     TEXT        REFERENCES ai_providers(id),
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_usage_log (
    id          BIGSERIAL   PRIMARY KEY,
    provider_id TEXT        REFERENCES ai_providers(id),
    user_id     TEXT        NOT NULL,
    endpoint    TEXT        NOT NULL,
    model       TEXT        NOT NULL,
    tokens_in   INTEGER,
    tokens_out  INTEGER,
    duration_ms INTEGER,
    status      TEXT        NOT NULL,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
