-- Migration 059: fix the orient-protocol tool name in the live
-- `mcp_server_instructions` singleton row (issue #115, v6.0.1).
--
-- Mirrors SQLite m055. Surgical REPLACE() preserves any admin
-- customisations elsewhere in the body.
--
-- Idempotent — running twice yields the same result.

UPDATE public.ai_creation_prompts
SET prompt_text = REPLACE(prompt_text,
                          'iris_package_hierarchy',
                          'package_hierarchy')
WHERE purpose = 'mcp_server_instructions';
