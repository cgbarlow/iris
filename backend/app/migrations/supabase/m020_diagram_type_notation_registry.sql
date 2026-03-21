-- Migration 020: Diagram type and notation registry (ADR-079).
-- Creates registry tables, adds notation columns to diagrams, and seeds data.

-- ── Registry tables ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS diagram_types (
    id            TEXT    PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    description   TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS notations (
    id            TEXT    PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    description   TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS diagram_type_notations (
    diagram_type_id TEXT    NOT NULL REFERENCES diagram_types(id),
    notation_id     TEXT    NOT NULL REFERENCES notations(id),
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (diagram_type_id, notation_id)
);

-- ── notation / detected_notations columns on diagrams ────────────────────────

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'diagrams' AND column_name = 'notation'
    ) THEN
        ALTER TABLE diagrams ADD COLUMN notation TEXT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'diagrams' AND column_name = 'detected_notations'
    ) THEN
        ALTER TABLE diagrams ADD COLUMN detected_notations TEXT;
    END IF;
END $$;

-- ── Seed diagram types ────────────────────────────────────────────────────────

INSERT INTO diagram_types (id, name, description, display_order) VALUES
    ('component',  'Component',  'A structural component diagram',              0),
    ('sequence',   'Sequence',   'A behavioural sequence diagram',              1),
    ('class',      'Class',      'A UML class diagram',                         2),
    ('deployment', 'Deployment', 'Infrastructure and deployment topology',      3),
    ('process',    'Process',    'A process or workflow diagram',               4),
    ('roadmap',    'Roadmap',    'A timeline or roadmap view',                  5),
    ('free_form',  'Free Form',  'Unrestricted canvas with any notation',       6)
ON CONFLICT (id) DO NOTHING;

-- ── Seed notations ────────────────────────────────────────────────────────────

INSERT INTO notations (id, name, description, display_order) VALUES
    ('simple',    'Simple',   'Non-technical boxes-and-lines notation',                          0),
    ('uml',       'UML',      'Unified Modeling Language notation',                              1),
    ('archimate', 'ArchiMate','ArchiMate enterprise architecture notation',                      2),
    ('c4',        'C4',       'C4 model notation (Context, Container, Component, Code)',         3)
ON CONFLICT (id) DO NOTHING;

-- ── Seed diagram_type ↔ notation mappings ─────────────────────────────────────

INSERT INTO diagram_type_notations (diagram_type_id, notation_id, is_default) VALUES
    -- component
    ('component', 'simple',    TRUE),
    ('component', 'uml',       FALSE),
    ('component', 'archimate', FALSE),
    ('component', 'c4',        FALSE),
    -- sequence
    ('sequence',  'simple',    FALSE),
    ('sequence',  'uml',       TRUE),
    -- class
    ('class',     'uml',       TRUE),
    -- deployment
    ('deployment','simple',    FALSE),
    ('deployment','uml',       FALSE),
    ('deployment','archimate', FALSE),
    ('deployment','c4',        TRUE),
    -- process
    ('process',   'simple',    FALSE),
    ('process',   'uml',       FALSE),
    ('process',   'archimate', TRUE),
    -- roadmap
    ('roadmap',   'simple',    TRUE),
    -- free_form
    ('free_form', 'simple',    TRUE),
    ('free_form', 'uml',       FALSE),
    ('free_form', 'archimate', FALSE),
    ('free_form', 'c4',        FALSE)
ON CONFLICT (diagram_type_id, notation_id) DO NOTHING;

-- ── Migrate existing diagrams: normalise diagram_type and set notation ─────────
-- Only rows where notation IS NULL have not yet been migrated.

UPDATE diagrams SET
    notation     = CASE diagram_type
                       WHEN 'uml'      THEN 'uml'
                       WHEN 'archimate'THEN 'archimate'
                       WHEN 'sequence' THEN 'uml'
                       WHEN 'roadmap'  THEN 'simple'
                       ELSE 'simple'
                   END,
    diagram_type = CASE diagram_type
                       WHEN 'uml'      THEN 'component'
                       WHEN 'archimate'THEN 'component'
                       WHEN 'simple'   THEN 'component'
                       WHEN 'sequence' THEN 'sequence'
                       WHEN 'roadmap'  THEN 'roadmap'
                       WHEN 'component'THEN 'component'
                       ELSE 'component'
                   END
WHERE notation IS NULL;
