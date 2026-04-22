-- Migration 041: Personal Access Tokens (ADR-127, SPEC-127-A).
-- PATs are long-lived bearer tokens for CLI / MCP / agent authentication.
-- Secrets are stored as Argon2id hashes; only the prefix is indexed.

CREATE TABLE IF NOT EXISTS personal_access_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  prefix TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pat_prefix ON personal_access_tokens(prefix);
CREATE INDEX IF NOT EXISTS idx_pat_user ON personal_access_tokens(user_id);

ALTER TABLE personal_access_tokens ENABLE ROW LEVEL SECURITY;

-- Owner-only read/write. The backend uses the service_role key for
-- prefix lookup at auth time (service role bypasses RLS), so anonymous
-- PAT verification works without the caller being authenticated against
-- Supabase.
CREATE POLICY IF NOT EXISTS pat_owner_select ON personal_access_tokens
  FOR SELECT USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS pat_owner_insert ON personal_access_tokens
  FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS pat_owner_update ON personal_access_tokens
  FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS pat_owner_delete ON personal_access_tokens
  FOR DELETE USING (user_id = auth.uid());
