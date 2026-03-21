-- Migration 030: Enable Row Level Security on all tables (ADR-095).
--
-- Strategy: deny-all. RLS is enabled with NO policies, which means:
--   - anon role (browser via Supabase JS): DENIED all table access
--   - authenticated role (logged-in user via Supabase JS): DENIED all table access
--   - postgres role (table owner, FastAPI backend via asyncpg): BYPASSES RLS
--   - service_role (Supabase admin key): BYPASSES RLS
--
-- This prevents the frontend-embedded anon key from being used to query tables
-- directly via the Supabase PostgREST API, closing a security gap where all Iris
-- auth and permission checks could be bypassed.
--
-- Each statement is idempotent — PostgreSQL ignores ENABLE ROW LEVEL SECURITY
-- if it is already enabled on a table.

-- m001: roles and auth
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;

-- m002: core content
ALTER TABLE sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE package_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE element_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationship_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagrams ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagram_versions ENABLE ROW LEVEL SECURITY;

-- m003: audit
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- m004: social
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;

-- m006: settings
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- m007: thumbnails
ALTER TABLE diagram_thumbnails ENABLE ROW LEVEL SECURITY;

-- m008–m009: tags
ALTER TABLE element_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagram_tags ENABLE ROW LEVEL SECURITY;

-- m015: package relationships
ALTER TABLE package_relationships ENABLE ROW LEVEL SECURITY;

-- m017: views
ALTER TABLE views ENABLE ROW LEVEL SECURITY;

-- m020: diagram type/notation registry
ALTER TABLE diagram_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE notations ENABLE ROW LEVEL SECURITY;
ALTER TABLE diagram_type_notations ENABLE ROW LEVEL SECURITY;

-- m021: edit locks
ALTER TABLE edit_locks ENABLE ROW LEVEL SECURITY;

-- m024: themes
ALTER TABLE themes ENABLE ROW LEVEL SECURITY;

-- m025: diagram links
ALTER TABLE diagram_links ENABLE ROW LEVEL SECURITY;

-- m026: AI providers
ALTER TABLE ai_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_log ENABLE ROW LEVEL SECURITY;

-- m027: profiles (Supabase auth bridge)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- m029: AI creation prompts
ALTER TABLE ai_creation_prompts ENABLE ROW LEVEL SECURITY;
