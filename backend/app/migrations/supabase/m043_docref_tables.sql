-- Migration 043: DocRef legislation tables (issue #24, ADR-135).
--
-- Postgres parity for the SQLite migration m034_docref_tables.py. Without
-- this file, Supabase deployments are missing docref_documents and
-- docref_chunks, and the Iris AI Legislation feature returns
-- "Failed to load documents" because /api/docref/documents queries a
-- non-existent table.
--
-- Schema mirrors SQLite m034 with Postgres types (TIMESTAMPTZ instead of
-- ISO TEXT). The DocRef service writes timestamps via datetime.isoformat();
-- the SupabaseAdapter (backend/app/db/adapter.py) coerces those strings to
-- datetime on insert and back to ISO strings on read, so the service code
-- works unchanged across both backends.

CREATE TABLE IF NOT EXISTS docref_documents (
    id              TEXT        PRIMARY KEY,
    slug            TEXT        NOT NULL,
    title           TEXT        NOT NULL,
    latest_version  TEXT        NOT NULL,
    source_url      TEXT        NOT NULL,
    csv_url         TEXT        NOT NULL,
    chunk_count     INTEGER     NOT NULL DEFAULT 0,
    status          TEXT        NOT NULL DEFAULT 'available',
    error_message   TEXT,
    imported_at     TIMESTAMPTZ,
    imported_by     TEXT,
    created_at      TIMESTAMPTZ NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL,
    UNIQUE (slug, latest_version)
);

CREATE INDEX IF NOT EXISTS idx_docref_documents_slug
    ON docref_documents (slug);

CREATE INDEX IF NOT EXISTS idx_docref_documents_status
    ON docref_documents (status);

CREATE TABLE IF NOT EXISTS docref_chunks (
    id           TEXT    PRIMARY KEY,
    document_id  TEXT    NOT NULL REFERENCES docref_documents (id) ON DELETE CASCADE,
    chunk_id     TEXT    NOT NULL,
    url          TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (document_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_docref_chunks_document_id
    ON docref_chunks (document_id);

-- RLS: DocRef tables are admin-managed (refresh + import) but readable by
-- all authenticated users so the Legislation picker works for everyone.
-- Mirrors the m034_extensions.sql policy shape.

ALTER TABLE docref_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE docref_chunks    ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'docref_documents' AND policyname = 'docref_documents_select') THEN
        CREATE POLICY "docref_documents_select" ON docref_documents FOR SELECT USING (TRUE);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'docref_documents' AND policyname = 'docref_documents_admin') THEN
        CREATE POLICY "docref_documents_admin" ON docref_documents FOR ALL USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        );
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'docref_chunks' AND policyname = 'docref_chunks_select') THEN
        CREATE POLICY "docref_chunks_select" ON docref_chunks FOR SELECT USING (TRUE);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'docref_chunks' AND policyname = 'docref_chunks_admin') THEN
        CREATE POLICY "docref_chunks_admin" ON docref_chunks FOR ALL USING (
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
        );
    END IF;
END $$;
