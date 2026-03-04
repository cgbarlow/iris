"""Migration m016: Rename entities→elements, split models→diagrams+packages (ADR-071).

User base is zero — no backwards compatibility needed.
Uses ALTER TABLE RENAME for simple renames and CREATE TABLE for splits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Rename tables and split models into diagrams + packages."""
    # Check if migration already ran
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
    )
    if await cursor.fetchone():
        return

    # Temporarily disable FK checks — we're recreating tables with new FK targets
    await db.execute("PRAGMA foreign_keys = OFF")

    # ---------- 1. Rename entities → elements ----------
    await db.execute("ALTER TABLE entities RENAME TO elements")
    await db.execute("ALTER TABLE entity_versions RENAME TO element_versions")

    # Rename entity_tags → element_tags
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entity_tags'"
    )
    if await cursor.fetchone():
        await db.execute("ALTER TABLE entity_tags RENAME TO element_tags")

    # ---------- 2. Rename relationships column references ----------
    # SQLite 3.35+ supports ALTER TABLE RENAME COLUMN
    await db.execute("ALTER TABLE relationships RENAME COLUMN source_entity_id TO source_element_id")
    await db.execute("ALTER TABLE relationships RENAME COLUMN target_entity_id TO target_element_id")
    # Note: relationship_versions does NOT have source/target columns — only relationships does.
    await db.execute("ALTER TABLE element_versions RENAME COLUMN entity_id TO element_id")

    # ---------- 3. Create packages table ----------
    await db.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id TEXT PRIMARY KEY,
            current_version INTEGER NOT NULL DEFAULT 1,
            parent_package_id TEXT REFERENCES packages(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            set_id TEXT REFERENCES sets(id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS package_versions (
            package_id TEXT NOT NULL REFERENCES packages(id),
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            data TEXT DEFAULT '{}',
            metadata TEXT,
            change_type TEXT NOT NULL DEFAULT 'create',
            change_summary TEXT,
            rollback_to INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (package_id, version)
        )
    """)

    # ---------- 4. Create diagrams table ----------
    await db.execute("""
        CREATE TABLE IF NOT EXISTS diagrams (
            id TEXT PRIMARY KEY,
            diagram_type TEXT NOT NULL DEFAULT 'simple',
            current_version INTEGER NOT NULL DEFAULT 1,
            parent_package_id TEXT REFERENCES packages(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            set_id TEXT REFERENCES sets(id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS diagram_versions (
            diagram_id TEXT NOT NULL REFERENCES diagrams(id),
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            data TEXT DEFAULT '{}',
            metadata TEXT,
            change_type TEXT NOT NULL DEFAULT 'create',
            change_summary TEXT,
            rollback_to INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (diagram_id, version)
        )
    """)

    # ---------- 5. Migrate model data ----------
    # Classify using model_type: 'package' → packages, everything else → diagrams.
    # The data column lives on model_versions, not models, so we classify by type.
    # Models with model_type='package' → packages (created by import for organizational containers)
    # All other models → diagrams (have canvas data)
    # If no model_type='package' exists yet, all models become diagrams (pre-rename state).

    await db.execute("""
        INSERT INTO packages (id, current_version, parent_package_id, created_at, created_by, updated_at, is_deleted, set_id)
        SELECT id, current_version, parent_model_id, created_at, created_by, updated_at, is_deleted, set_id
        FROM models
        WHERE model_type = 'package'
    """)

    await db.execute("""
        INSERT INTO package_versions (package_id, version, name, description, data, metadata, change_type, change_summary, rollback_to, created_at, created_by)
        SELECT mv.model_id, mv.version, mv.name, mv.description, mv.data, mv.metadata, mv.change_type, mv.change_summary, mv.rollback_to, mv.created_at, mv.created_by
        FROM model_versions mv
        INNER JOIN packages p ON p.id = mv.model_id
    """)

    await db.execute("""
        INSERT INTO diagrams (id, diagram_type, current_version, parent_package_id, created_at, created_by, updated_at, is_deleted, set_id)
        SELECT id, model_type, current_version, parent_model_id, created_at, created_by, updated_at, is_deleted, set_id
        FROM models
        WHERE model_type != 'package'
    """)

    await db.execute("""
        INSERT INTO diagram_versions (diagram_id, version, name, description, data, metadata, change_type, change_summary, rollback_to, created_at, created_by)
        SELECT mv.model_id, mv.version, mv.name, mv.description, mv.data, mv.metadata, mv.change_type, mv.change_summary, mv.rollback_to, mv.created_at, mv.created_by
        FROM model_versions mv
        INNER JOIN diagrams d ON d.id = mv.model_id
    """)

    # ---------- 6. Rename model_relationships → package_relationships ----------
    await db.execute("""
        CREATE TABLE IF NOT EXISTS package_relationships (
            id TEXT PRIMARY KEY,
            source_package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
            target_package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
            relationship_type TEXT NOT NULL,
            label TEXT,
            description TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source_package_id, target_package_id, relationship_type)
        )
    """)

    await db.execute("""
        INSERT OR IGNORE INTO package_relationships (id, source_package_id, target_package_id, relationship_type, label, description, created_by, created_at)
        SELECT id, source_model_id, target_model_id, relationship_type, label, description, created_by, created_at
        FROM model_relationships
        WHERE source_model_id IN (SELECT id FROM packages)
        AND target_model_id IN (SELECT id FROM packages)
    """)

    # ---------- 7. Create diagram_tags ----------
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='model_tags'"
    )
    if await cursor.fetchone():
        await db.execute("""
            CREATE TABLE IF NOT EXISTS diagram_tags (
                diagram_id TEXT NOT NULL REFERENCES diagrams(id),
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_by TEXT,
                PRIMARY KEY (diagram_id, tag)
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO diagram_tags (diagram_id, tag, created_at, created_by)
            SELECT model_id, tag, created_at, created_by FROM model_tags
            WHERE model_id IN (SELECT id FROM diagrams)
        """)

    # ---------- 7b. Rename element_tags.entity_id → element_id ----------
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='element_tags'"
    )
    if await cursor.fetchone():
        # Check if column still named entity_id
        col_cursor = await db.execute("PRAGMA table_info(element_tags)")
        col_names = [r[1] for r in await col_cursor.fetchall()]
        if "entity_id" in col_names:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS element_tags_new (
                    element_id TEXT NOT NULL REFERENCES elements(id),
                    tag TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    created_by TEXT,
                    PRIMARY KEY (element_id, tag)
                )
            """)
            await db.execute("""
                INSERT OR IGNORE INTO element_tags_new (element_id, tag, created_at, created_by)
                SELECT entity_id, tag, created_at, created_by FROM element_tags
            """)
            await db.execute("DROP TABLE element_tags")
            await db.execute("ALTER TABLE element_tags_new RENAME TO element_tags")

    # ---------- 8. Create indexes ----------
    await db.execute("CREATE INDEX IF NOT EXISTS idx_packages_set ON packages(set_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_packages_parent ON packages(parent_package_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_diagrams_set ON diagrams(set_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_diagrams_parent ON diagrams(parent_package_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_diagrams_type ON diagrams(diagram_type)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_pkg_rel_source ON package_relationships(source_package_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_pkg_rel_target ON package_relationships(target_package_id)")

    # ---------- 9. Rebuild FTS5 tables ----------
    # FTS5 virtual tables cannot be renamed — drop and recreate
    await db.execute("DROP TABLE IF EXISTS entities_fts")
    await db.execute("DROP TABLE IF EXISTS models_fts")
    await db.execute("DROP TABLE IF EXISTS search_index")

    await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS elements_fts USING fts5(
            element_id UNINDEXED,
            name,
            element_type UNINDEXED,
            description,
            tokenize='porter unicode61'
        )
    """)

    await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS diagrams_fts USING fts5(
            diagram_id UNINDEXED,
            name,
            diagram_type UNINDEXED,
            description,
            tokenize='porter unicode61'
        )
    """)

    # ---------- 10. Rename elements.entity_type → element_type ----------
    await db.execute("ALTER TABLE elements RENAME COLUMN entity_type TO element_type")

    # ---------- 11. Recreate tables with stale foreign keys ----------
    # Several tables have FK REFERENCES models(id) which is being dropped.
    # SQLite can't ALTER FK constraints, so recreate these tables.

    # 11a. Recreate model_thumbnails → diagram_thumbnails with correct FK
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='model_thumbnails'"
    )
    if await cursor.fetchone():
        await db.execute("""
            CREATE TABLE IF NOT EXISTS diagram_thumbnails (
                diagram_id TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'dark',
                thumbnail BLOB NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (diagram_id, theme),
                FOREIGN KEY (diagram_id) REFERENCES diagrams(id)
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO diagram_thumbnails (diagram_id, theme, thumbnail, updated_at)
            SELECT model_id, theme, thumbnail, updated_at FROM model_thumbnails
            WHERE model_id IN (SELECT id FROM diagrams)
        """)
        await db.execute("DROP TABLE model_thumbnails")

    # 11b. Recreate bookmarks with correct FK and column name
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks_new (
            user_id TEXT NOT NULL REFERENCES users(id),
            diagram_id TEXT NOT NULL REFERENCES diagrams(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, diagram_id)
        )
    """)
    await db.execute("""
        INSERT OR IGNORE INTO bookmarks_new (user_id, diagram_id, created_at)
        SELECT user_id, model_id, created_at FROM bookmarks
        WHERE model_id IN (SELECT id FROM diagrams)
    """)
    await db.execute("DROP TABLE bookmarks")
    await db.execute("ALTER TABLE bookmarks_new RENAME TO bookmarks")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_diagram ON bookmarks(diagram_id)")

    # 11c. Recreate comments with updated target_type CHECK constraint
    await db.execute("""
        CREATE TABLE IF NOT EXISTS comments_new (
            id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL CHECK (target_type IN ('element', 'diagram')),
            target_id TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    """)
    await db.execute("""
        INSERT OR IGNORE INTO comments_new (id, target_type, target_id, user_id, content,
            created_at, updated_at, is_deleted)
        SELECT id,
            CASE target_type WHEN 'entity' THEN 'element' WHEN 'model' THEN 'diagram' ELSE target_type END,
            target_id, user_id, content, created_at, updated_at, is_deleted
        FROM comments
    """)
    await db.execute("DROP TABLE comments")
    await db.execute("ALTER TABLE comments_new RENAME TO comments")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_comments_target ON comments(target_type, target_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id)")

    # 11d. Recreate sets table with correct FK on thumbnail_diagram_id
    # Use partial unique index (from m014) instead of full UNIQUE on name
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sets_new (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            thumbnail_source TEXT,
            thumbnail_diagram_id TEXT REFERENCES diagrams(id),
            thumbnail_image BLOB
        )
    """)
    await db.execute("""
        INSERT OR IGNORE INTO sets_new (id, name, description, created_at, created_by,
            updated_at, is_deleted, thumbnail_source, thumbnail_diagram_id, thumbnail_image)
        SELECT id, name, description, created_at, created_by,
            updated_at, is_deleted, thumbnail_source, thumbnail_model_id, thumbnail_image
        FROM sets
    """)
    await db.execute("DROP TABLE sets")
    await db.execute("ALTER TABLE sets_new RENAME TO sets")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_sets_name ON sets(name)")
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_sets_name_active ON sets(name) WHERE is_deleted = 0"
    )

    # ---------- 12. Drop old tables ----------
    await db.execute("DROP TABLE IF EXISTS model_tags")
    await db.execute("DROP TABLE IF EXISTS model_relationships")
    await db.execute("DROP TABLE IF EXISTS model_versions")
    await db.execute("DROP TABLE IF EXISTS models")
    # entities/entity_versions already renamed via ALTER TABLE

    await db.commit()

    # Re-enable foreign key checks
    await db.execute("PRAGMA foreign_keys = ON")
