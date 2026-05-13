-- Migration 060: fix the orient-protocol tool name in per-scope
-- `mcp_system_context` fields on sets and collections (issue #115
-- follow-up, v6.0.2).
--
-- Mirrors SQLite m056. Surgical REPLACE() preserves any admin
-- customisations elsewhere in the body.
--
-- Idempotent — running twice yields the same result.

UPDATE public.sets
SET mcp_system_context = REPLACE(mcp_system_context,
                                 'iris_package_hierarchy',
                                 'package_hierarchy')
WHERE mcp_system_context IS NOT NULL;

UPDATE public.collections
SET mcp_system_context = REPLACE(mcp_system_context,
                                 'iris_package_hierarchy',
                                 'package_hierarchy')
WHERE mcp_system_context IS NOT NULL;
