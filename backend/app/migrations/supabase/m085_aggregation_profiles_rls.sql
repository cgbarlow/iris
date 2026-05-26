-- Migration 085: enable Row Level Security on tables that slipped past
-- the m030 sweep (issue #236).
--
-- Three tables were created after m030 without `ENABLE ROW LEVEL
-- SECURITY`:
--   - public.artefacts            (m064, v6.2.0)
--   - public.element_templates    (m071, v6.11.0)
--   - public.aggregation_profiles (m081, v6.28.0)
--
-- Per ADR-095, every Supabase table uses the deny-all strategy: RLS is
-- enabled with no policies, so the embedded `anon` key (and any
-- `authenticated` JWT) cannot reach the table via PostgREST. The
-- FastAPI backend connects as the `postgres` role (table owner) and
-- bypasses RLS — application-layer RBAC is unchanged.
--
-- Idempotent: PostgreSQL ignores ENABLE ROW LEVEL SECURITY when it is
-- already enabled on a table.

ALTER TABLE public.artefacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.element_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.aggregation_profiles ENABLE ROW LEVEL SECURITY;
