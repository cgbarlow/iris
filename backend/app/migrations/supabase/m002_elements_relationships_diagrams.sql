-- Migration 002: Elements, relationships, diagrams, packages and version tables.
-- Per SPEC-006-A (Entity Versioning) and SPEC-003-A (Entity Domain Model).
-- NOTE: Creates tables with final names from m016 (elements/diagrams) directly,
--       skipping the intermediate entities/models naming.

-- ── Sets table (needed before elements/diagrams for FK references) ────────────
-- Sets are created here so elements and diagrams can reference them.
-- Full set definition (including m012/m013/m014 changes) is in m002 since
-- PostgreSQL uses final names directly.

CREATE TABLE IF NOT EXISTS sets (
    id                   TEXT        PRIMARY KEY,
    name                 TEXT        NOT NULL,
    description          TEXT,
    created_at           TIMESTAMPTZ NOT NULL,
    created_by           TEXT        NOT NULL,
    updated_at           TIMESTAMPTZ NOT NULL,
    is_deleted           BOOLEAN     NOT NULL DEFAULT FALSE,
    thumbnail_source     TEXT,
    thumbnail_diagram_id TEXT,
    thumbnail_image      BYTEA
);

CREATE INDEX IF NOT EXISTS idx_sets_name ON sets(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sets_name_active ON sets(name) WHERE is_deleted = FALSE;

-- Seed Default set
INSERT INTO sets (id, name, description, created_at, created_by, updated_at)
VALUES ('00000000-0000-0000-0000-000000000001', 'Default', 'Default set for all items', NOW(), 'system', NOW())
ON CONFLICT (id) DO NOTHING;

-- ── Packages table ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS packages (
    id               TEXT        PRIMARY KEY,
    current_version  INTEGER     NOT NULL DEFAULT 1,
    parent_package_id TEXT       REFERENCES packages(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by       TEXT        NOT NULL DEFAULT '',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted       BOOLEAN     NOT NULL DEFAULT FALSE,
    deleted_group_id TEXT,
    set_id           TEXT        REFERENCES sets(id)
);

CREATE INDEX IF NOT EXISTS idx_packages_set     ON packages(set_id);
CREATE INDEX IF NOT EXISTS idx_packages_parent  ON packages(parent_package_id);
CREATE INDEX IF NOT EXISTS idx_packages_deleted_group ON packages(deleted_group_id) WHERE deleted_group_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS package_versions (
    package_id    TEXT        NOT NULL REFERENCES packages(id),
    version       INTEGER     NOT NULL,
    name          TEXT        NOT NULL,
    description   TEXT,
    data          TEXT        DEFAULT '{}',
    metadata      TEXT,
    change_type   TEXT        NOT NULL DEFAULT 'create',
    change_summary TEXT,
    rollback_to   INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by    TEXT        NOT NULL DEFAULT '',
    PRIMARY KEY (package_id, version)
);

-- ── Elements (formerly entities) ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS elements (
    id              TEXT        PRIMARY KEY,
    element_type    TEXT        NOT NULL,
    current_version INTEGER     NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      TEXT        NOT NULL REFERENCES users(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted      BOOLEAN     NOT NULL DEFAULT FALSE,
    deleted_group_id TEXT,
    set_id          TEXT        REFERENCES sets(id),
    notation        TEXT        DEFAULT 'simple',
    search_vector   TSVECTOR
);

CREATE INDEX IF NOT EXISTS idx_elements_type          ON elements(element_type);
CREATE INDEX IF NOT EXISTS idx_elements_created_by    ON elements(created_by);
CREATE INDEX IF NOT EXISTS idx_elements_set           ON elements(set_id);
CREATE INDEX IF NOT EXISTS idx_elements_deleted_group ON elements(deleted_group_id) WHERE deleted_group_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_elements_search        ON elements USING GIN(search_vector);

CREATE TABLE IF NOT EXISTS element_versions (
    element_id     TEXT        NOT NULL REFERENCES elements(id),
    version        INTEGER     NOT NULL,
    name           TEXT        NOT NULL,
    description    TEXT,
    data           TEXT        NOT NULL,
    metadata       TEXT,
    change_type    TEXT        NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete', 'restore')),
    change_summary TEXT,
    rollback_to    INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by     TEXT        NOT NULL REFERENCES users(id),
    PRIMARY KEY (element_id, version)
);

CREATE INDEX IF NOT EXISTS idx_element_versions_created_at ON element_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_element_versions_created_by ON element_versions(created_by);

-- ── Relationships ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS relationships (
    id               TEXT        PRIMARY KEY,
    source_element_id TEXT       NOT NULL REFERENCES elements(id),
    target_element_id TEXT       NOT NULL REFERENCES elements(id),
    relationship_type TEXT       NOT NULL,
    current_version  INTEGER     NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by       TEXT        NOT NULL REFERENCES users(id),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted       BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_relationships_source     ON relationships(source_element_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target     ON relationships(target_element_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type       ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_created_by ON relationships(created_by);

CREATE TABLE IF NOT EXISTS relationship_versions (
    relationship_id TEXT        NOT NULL REFERENCES relationships(id),
    version         INTEGER     NOT NULL,
    label           TEXT,
    description     TEXT,
    data            TEXT,
    metadata        TEXT,
    change_type     TEXT        NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete', 'restore')),
    change_summary  TEXT,
    rollback_to     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      TEXT        NOT NULL REFERENCES users(id),
    PRIMARY KEY (relationship_id, version)
);

CREATE INDEX IF NOT EXISTS idx_rel_versions_created_at ON relationship_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_rel_versions_created_by ON relationship_versions(created_by);

-- ── Diagrams (formerly models) ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS diagrams (
    id               TEXT        PRIMARY KEY,
    diagram_type     TEXT        NOT NULL DEFAULT 'simple',
    current_version  INTEGER     NOT NULL DEFAULT 1,
    parent_package_id TEXT       REFERENCES packages(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by       TEXT        NOT NULL DEFAULT '',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted       BOOLEAN     NOT NULL DEFAULT FALSE,
    deleted_group_id TEXT,
    set_id           TEXT        REFERENCES sets(id),
    notation         TEXT,
    detected_notations TEXT,
    search_vector    TSVECTOR
);

CREATE INDEX IF NOT EXISTS idx_diagrams_set           ON diagrams(set_id);
CREATE INDEX IF NOT EXISTS idx_diagrams_parent        ON diagrams(parent_package_id);
CREATE INDEX IF NOT EXISTS idx_diagrams_type          ON diagrams(diagram_type);
CREATE INDEX IF NOT EXISTS idx_diagrams_deleted_group ON diagrams(deleted_group_id) WHERE deleted_group_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_diagrams_search        ON diagrams USING GIN(search_vector);

CREATE TABLE IF NOT EXISTS diagram_versions (
    diagram_id     TEXT        NOT NULL REFERENCES diagrams(id),
    version        INTEGER     NOT NULL,
    name           TEXT        NOT NULL,
    description    TEXT,
    data           TEXT        DEFAULT '{}',
    metadata       TEXT,
    change_type    TEXT        NOT NULL DEFAULT 'create',
    change_summary TEXT,
    rollback_to    INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by     TEXT        NOT NULL DEFAULT '',
    PRIMARY KEY (diagram_id, version)
);

-- ── Add FK on sets.thumbnail_diagram_id now that diagrams exists ──────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'sets_thumbnail_diagram_id_fkey'
          AND table_name = 'sets'
    ) THEN
        ALTER TABLE sets
            ADD CONSTRAINT sets_thumbnail_diagram_id_fkey
            FOREIGN KEY (thumbnail_diagram_id) REFERENCES diagrams(id);
    END IF;
END $$;

-- ── FTS triggers for elements ─────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION elements_search_vector_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_name        TEXT;
    v_description TEXT;
BEGIN
    -- Pull latest version name/description for this element
    SELECT ev.name, ev.description
      INTO v_name, v_description
      FROM element_versions ev
     WHERE ev.element_id = NEW.id
     ORDER BY ev.version DESC
     LIMIT 1;

    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(v_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(v_description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.element_type, '')), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_elements ON elements;
CREATE TRIGGER tsvectorupdate_elements
    BEFORE INSERT OR UPDATE ON elements
    FOR EACH ROW EXECUTE FUNCTION elements_search_vector_update();

-- ── FTS triggers for diagrams ─────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION diagrams_search_vector_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_name        TEXT;
    v_description TEXT;
BEGIN
    SELECT dv.name, dv.description
      INTO v_name, v_description
      FROM diagram_versions dv
     WHERE dv.diagram_id = NEW.id
     ORDER BY dv.version DESC
     LIMIT 1;

    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(v_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(v_description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.diagram_type, '')), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_diagrams ON diagrams;
CREATE TRIGGER tsvectorupdate_diagrams
    BEFORE INSERT OR UPDATE ON diagrams
    FOR EACH ROW EXECUTE FUNCTION diagrams_search_vector_update();
