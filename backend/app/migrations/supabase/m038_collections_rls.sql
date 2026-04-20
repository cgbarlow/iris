-- Migration 038: Enable RLS on collections table.
-- collections was added in m033 but RLS was not enabled, allowing direct
-- PostgREST access via the anon key. This closes that gap.
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
