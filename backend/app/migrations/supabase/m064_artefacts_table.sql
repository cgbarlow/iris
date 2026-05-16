-- Migration 064: artefacts table (ADR-179, SPEC-179-A, v6.2.0).
--
-- Issue #133 Phase 2. Mirrors SQLite m060. Generic artefact store
-- for rendered markdown / docx / pdf documents.

CREATE TABLE IF NOT EXISTS public.artefacts (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    bytes BYTEA NOT NULL,
    size_bytes INTEGER NOT NULL,
    source_kind TEXT NOT NULL,
    source_ref TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_artefacts_source_ref
    ON public.artefacts(source_ref);
