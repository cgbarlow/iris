-- Migration 071: Element Templates table (ADR-191, issue #153).
--
-- Mirrors SQLite m067. Captures a snapshot of selected fields from an
-- existing element so later element creation can be pre-filled from
-- the template. Set-scoped by default with optional is_global
-- promotion; CHECK constraint enforces scoping consistency.
--
-- Idempotent. Protocol §15: booleans use TRUE/FALSE literals on
-- Postgres (NOT integer 0/1 — `is_global` and `is_deleted` are
-- declared BOOLEAN here).

CREATE TABLE IF NOT EXISTS public.element_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    set_id TEXT REFERENCES public.sets(id),
    is_global BOOLEAN NOT NULL DEFAULT FALSE,
    source_element_id TEXT REFERENCES public.elements(id),
    included_fields TEXT NOT NULL,
    template_data TEXT NOT NULL,
    created_by TEXT REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT element_templates_scoping_consistent CHECK (
        (is_global = TRUE AND set_id IS NULL) OR
        (is_global = FALSE AND set_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_element_templates_set
    ON public.element_templates(set_id) WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_element_templates_global
    ON public.element_templates(is_global)
    WHERE is_global = TRUE AND is_deleted = FALSE;
