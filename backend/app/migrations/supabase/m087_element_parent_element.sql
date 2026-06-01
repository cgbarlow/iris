-- Migration 087: Element → parent element containment (ADR-231).
--
-- Adds nullable self-referencing ``parent_element_id`` column to
-- ``elements`` plus an index. The element-containment axis: an element owns
-- child elements, so Sparx EA nestedClassifier trees (GEANZ capability zone
-- → capability → sub-capability) import with depth. Orthogonal to
-- ``package_id`` (ADR-184) and ``detail_diagram_id`` (ADR-221).
-- Mirrors SQLite m081.
--
-- Idempotent.

ALTER TABLE public.elements
    ADD COLUMN IF NOT EXISTS parent_element_id TEXT REFERENCES public.elements(id);

CREATE INDEX IF NOT EXISTS idx_elements_parent_element
    ON public.elements(parent_element_id);
