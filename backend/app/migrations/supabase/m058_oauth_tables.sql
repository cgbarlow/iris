-- Migration 058: OAuth 2.1 Authorization Server tables (ADR-164, SPEC-164-A).
--
-- Mirrors SQLite m054. Replaces the v5.15.0 pairing flow with full OAuth
-- 2.1 for iris-mcp HTTP transport.
--
-- Idempotent.

-- 1. Drop the v5.15.0 pairing-flow remnant.
DROP TABLE IF EXISTS public.pairing_codes;

-- 2. oauth_clients — DCR registrations.
CREATE TABLE IF NOT EXISTS public.oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret_hash TEXT,
    client_name TEXT NOT NULL,
    redirect_uris JSONB NOT NULL,
    grant_types JSONB NOT NULL DEFAULT '["authorization_code","refresh_token"]'::jsonb,
    token_endpoint_auth_method TEXT NOT NULL DEFAULT 'none',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

ALTER TABLE public.oauth_clients ENABLE ROW LEVEL SECURITY;
-- Service role only — managed via the OAuth router endpoints.

-- 3. oauth_authorization_codes — short-lived PKCE codes.
CREATE TABLE IF NOT EXISTS public.oauth_authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    redirect_uri TEXT NOT NULL,
    code_challenge TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL DEFAULT 'S256',
    scope TEXT NOT NULL DEFAULT 'iris',
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oauth_codes_expires
    ON public.oauth_authorization_codes(expires_at);

ALTER TABLE public.oauth_authorization_codes ENABLE ROW LEVEL SECURITY;

-- 4. oauth_refresh_tokens — DB-stored for revocability, family-id for rotation.
CREATE TABLE IF NOT EXISTS public.oauth_refresh_tokens (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES public.oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    family_id TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at TIMESTAMPTZ,
    revoked BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_oauth_refresh_user
    ON public.oauth_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_family
    ON public.oauth_refresh_tokens(family_id);

ALTER TABLE public.oauth_refresh_tokens ENABLE ROW LEVEL SECURITY;

-- Owner-only refresh-token visibility (token endpoint runs with service
-- role so it bypasses RLS; per-user direct reads are gated to the owner).
DROP POLICY IF EXISTS oauth_refresh_tokens_owner_select ON public.oauth_refresh_tokens;
CREATE POLICY oauth_refresh_tokens_owner_select ON public.oauth_refresh_tokens
    FOR SELECT USING (user_id = auth.uid());
