-- Migration 056: MCP pairing codes (ADR-160, SPEC-160-A).
--
-- Mirrors SQLite migration m052_mcp_pairing_codes.py. Pairing codes
-- are short typeable one-shot credentials used by the in-app MCP
-- pairing flow. Exchange issues a fresh PAT via the existing
-- personal_access_tokens machinery.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.pairing_codes (
  code TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  exchanged_at TIMESTAMPTZ,
  issued_pat_id UUID,
  issued_pat_name TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pairing_codes_user ON public.pairing_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_pairing_codes_expires ON public.pairing_codes(expires_at);

ALTER TABLE public.pairing_codes ENABLE ROW LEVEL SECURITY;

-- The backend uses the service_role key for the anonymous /exchange
-- endpoint, so service role bypasses RLS. Owner-only read/write below
-- mirrors personal_access_tokens (ADR-127, m042) and supports any
-- future direct-from-frontend reads.

DROP POLICY IF EXISTS pairing_codes_owner_select ON public.pairing_codes;
CREATE POLICY pairing_codes_owner_select ON public.pairing_codes
  FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS pairing_codes_owner_insert ON public.pairing_codes;
CREATE POLICY pairing_codes_owner_insert ON public.pairing_codes
  FOR INSERT WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS pairing_codes_owner_update ON public.pairing_codes;
CREATE POLICY pairing_codes_owner_update ON public.pairing_codes
  FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS pairing_codes_owner_delete ON public.pairing_codes;
CREATE POLICY pairing_codes_owner_delete ON public.pairing_codes
  FOR DELETE USING (user_id = auth.uid());
