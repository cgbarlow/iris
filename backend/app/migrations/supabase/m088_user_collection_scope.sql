-- Migration 088: Per-user collection write-scope (ADR-237).
--
-- Mirrors SQLite m082. Junction table whitelisting the collections a user may
-- WRITE in. No rows for a user = unscoped (writes everywhere, pre-ADR-237
-- behaviour). Reads are unaffected (ADR-123).
--
-- ``user_id`` references ``profiles(id)`` (the Supabase user store), mirroring
-- how the SQLite half references ``users(id)``.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS user_collection_scope (
    user_id       UUID        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    collection_id TEXT        NOT NULL REFERENCES public.collections(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, collection_id)
);

CREATE INDEX IF NOT EXISTS idx_ucs_user
    ON public.user_collection_scope(user_id);

ALTER TABLE public.user_collection_scope ENABLE ROW LEVEL SECURITY;
