"""v5.5.1 (issue #46 item #4 root cause): static-parser test for the
new Postgres migration that converts images.id and images.uploaded_by
from UUID to TEXT.

Pre-fix the columns were declared as UUID in m046_images.sql, but
Iris user IDs are TEXT and the Python service passes
`image_id = str(uuid.uuid4())`. asyncpg doesn't auto-coerce
strings to UUIDs, so /api/images returned 500 — the markdown
editor's onpaste catch swallowed the failure and users saw 'ctrl-v
does nothing'.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "app" / "migrations" / "supabase" / "m049_images_uuid_to_text.sql"


def test_migration_exists() -> None:
    assert MIGRATION.is_file()


def test_alters_id_from_uuid_to_text() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ALTER TABLE images ALTER COLUMN id" in sql
    assert "TYPE TEXT" in sql
    assert "id::text" in sql


def test_alters_uploaded_by_from_uuid_to_text() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ALTER TABLE images ALTER COLUMN uploaded_by" in sql
    assert "uploaded_by::text" in sql


def test_drops_default_on_id_column() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    # The original had `DEFAULT gen_random_uuid()` which is incompatible
    # with TEXT type; the migration must drop the default first.
    assert "ALTER COLUMN id DROP DEFAULT" in sql


def test_idempotent_via_information_schema_guard() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    # The ALTERs are guarded by `IF EXISTS … data_type = 'uuid'` so
    # re-running the migration on a TEXT-shaped table is a no-op.
    assert "information_schema.columns" in sql
    assert "data_type = 'uuid'" in sql
