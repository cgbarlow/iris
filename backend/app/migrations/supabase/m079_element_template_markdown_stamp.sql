-- Migration 079: markdown_stamp column on element_templates (ADR-211).
--
-- Mirrors SQLite m074. Adds a TEXT column that holds a smart-markdown
-- fragment using `{{self:<field-spec>}}` placeholders, resolved by the
-- picker at insert time. Seeded by m080 with five global stamps.
--
-- Idempotent.

ALTER TABLE public.element_templates
    ADD COLUMN IF NOT EXISTS markdown_stamp TEXT;
