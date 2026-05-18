-- Migration 075: rename 'text' diagram type to 'Standard Markdown' (v6.14.1).
--
-- Mirrors SQLite m071. The diagram_type id stays 'text' — only the
-- display name and description change. Existing diagrams keep working
-- with no re-pointing.
--
-- Idempotent (UPDATE is naturally so).

UPDATE public.diagram_types
SET name = 'Standard Markdown',
    description = 'Plain markdown source rendered as a document with TOC drawer'
WHERE id = 'text';
