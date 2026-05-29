-- Migration 086: Element → detail diagram drill link (ADR-221).
--
-- Adds nullable ``detail_diagram_id`` column to ``elements`` plus an
-- index. The Sparx EA "composite element" drill: an element points at
-- the diagram that elaborates it.
-- Mirrors SQLite m080.
--
-- Idempotent.

ALTER TABLE public.elements
    ADD COLUMN IF NOT EXISTS detail_diagram_id TEXT REFERENCES public.diagrams(id);

CREATE INDEX IF NOT EXISTS idx_elements_detail_diagram
    ON public.elements(detail_diagram_id);
