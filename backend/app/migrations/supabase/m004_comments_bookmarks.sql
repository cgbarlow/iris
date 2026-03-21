-- Migration 004: Comments and bookmarks tables.
-- Per SPEC-003-A.
-- NOTE: Uses final column names / CHECK values from m016 (element/diagram
--       instead of entity/model).  Bookmarks also uses final schema from m018
--       (package_id support, rowid-based).

-- ── Comments ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS comments (
    id          TEXT        PRIMARY KEY,
    target_type TEXT        NOT NULL CHECK (target_type IN ('element', 'diagram')),
    target_id   TEXT        NOT NULL,
    user_id     TEXT        NOT NULL REFERENCES users(id),
    content     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted  BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_comments_target     ON comments(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_comments_user       ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- ── Bookmarks (per-user diagram / package bookmarks) ──────────────────────────
-- Final schema from m016 + m018: supports both diagram_id and package_id.
-- Exactly one of diagram_id / package_id must be non-NULL.

CREATE TABLE IF NOT EXISTS bookmarks (
    user_id    TEXT        NOT NULL REFERENCES users(id),
    diagram_id TEXT        REFERENCES diagrams(id),
    package_id TEXT        REFERENCES packages(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (diagram_id IS NOT NULL AND package_id IS NULL)
        OR (diagram_id IS NULL AND package_id IS NOT NULL)
    ),
    UNIQUE (user_id, diagram_id),
    UNIQUE (user_id, package_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_diagram ON bookmarks(diagram_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_package ON bookmarks(package_id);
