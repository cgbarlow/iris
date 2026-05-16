-- Migration 070: Allow ``class`` diagram type under ``simple`` notation
-- (ADR-188, issue #160).
--
-- Mirrors SQLite m066. Inserts the missing (class, simple) pair so the
-- new-element dropdown surfaces ``class`` when the user picks the simple
-- notation. Idempotent.
--
-- Protocol §15: `is_default` is BOOLEAN on Postgres — use FALSE literal,
-- not 0.

INSERT INTO public.diagram_type_notations (diagram_type_id, notation_id, is_default)
VALUES ('class', 'simple', FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;
