-- Migration 040: Full search parity with SQLite (ADR-125).
--
-- Three independent fixes in one migration:
--
--   1. Add `search_vector` + GIN + triggers for packages, sets, collections
--      (previously only elements and diagrams had these on PostgreSQL).
--
--   2. Fix the INSERT-ordering gap on elements/diagrams. The existing
--      `BEFORE INSERT OR UPDATE` triggers on elements/diagrams read from
--      element_versions/diagram_versions, but services insert the version
--      row AFTER the parent row, so parent.search_vector is empty on
--      first create. Added chain-triggers on the *_versions tables that
--      perform a no-op UPDATE on the parent row, re-firing the parent's
--      BEFORE trigger with the version row now present. Same pattern for
--      the new package chain.
--
--   3. Backfill every existing row in all five entity tables by writing
--      a no-op UPDATE that re-fires the BEFORE triggers, so UAT data
--      becomes searchable immediately on deploy without a separate
--      script.

-- ── Packages ─────────────────────────────────────────────────────────────
ALTER TABLE packages ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
CREATE INDEX IF NOT EXISTS idx_packages_search ON packages USING GIN(search_vector);

CREATE OR REPLACE FUNCTION packages_search_vector_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_name        TEXT;
    v_description TEXT;
BEGIN
    SELECT pv.name, pv.description
      INTO v_name, v_description
      FROM package_versions pv
     WHERE pv.package_id = NEW.id
     ORDER BY pv.version DESC
     LIMIT 1;

    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(v_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(v_description, '')), 'B');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_packages ON packages;
CREATE TRIGGER tsvectorupdate_packages
    BEFORE INSERT OR UPDATE ON packages
    FOR EACH ROW EXECUTE FUNCTION packages_search_vector_update();

-- ── Sets (no version table — name/description on the row itself) ─────────
ALTER TABLE sets ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
CREATE INDEX IF NOT EXISTS idx_sets_search ON sets USING GIN(search_vector);

CREATE OR REPLACE FUNCTION sets_search_vector_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_sets ON sets;
CREATE TRIGGER tsvectorupdate_sets
    BEFORE INSERT OR UPDATE ON sets
    FOR EACH ROW EXECUTE FUNCTION sets_search_vector_update();

-- ── Collections (no version table) ───────────────────────────────────────
ALTER TABLE collections ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
CREATE INDEX IF NOT EXISTS idx_collections_search ON collections USING GIN(search_vector);

CREATE OR REPLACE FUNCTION collections_search_vector_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_collections ON collections;
CREATE TRIGGER tsvectorupdate_collections
    BEFORE INSERT OR UPDATE ON collections
    FOR EACH ROW EXECUTE FUNCTION collections_search_vector_update();

-- ── Chain triggers: re-fire parent BEFORE trigger after version insert ───
-- Why: parent BEFORE triggers read the latest version from the *_versions
-- table, but services insert the version row AFTER the parent row. On
-- initial create the parent's search_vector is therefore empty. These
-- AFTER-INSERT triggers on the version tables write a no-op UPDATE to the
-- parent that re-fires the parent's BEFORE trigger, by which time the
-- version row is visible.

CREATE OR REPLACE FUNCTION elements_reindex_from_version()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE elements SET current_version = current_version
     WHERE id = NEW.element_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_element_versions ON element_versions;
CREATE TRIGGER tsvectorupdate_element_versions
    AFTER INSERT OR UPDATE ON element_versions
    FOR EACH ROW EXECUTE FUNCTION elements_reindex_from_version();

CREATE OR REPLACE FUNCTION diagrams_reindex_from_version()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE diagrams SET current_version = current_version
     WHERE id = NEW.diagram_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_diagram_versions ON diagram_versions;
CREATE TRIGGER tsvectorupdate_diagram_versions
    AFTER INSERT OR UPDATE ON diagram_versions
    FOR EACH ROW EXECUTE FUNCTION diagrams_reindex_from_version();

CREATE OR REPLACE FUNCTION packages_reindex_from_version()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE packages SET current_version = current_version
     WHERE id = NEW.package_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tsvectorupdate_package_versions ON package_versions;
CREATE TRIGGER tsvectorupdate_package_versions
    AFTER INSERT OR UPDATE ON package_versions
    FOR EACH ROW EXECUTE FUNCTION packages_reindex_from_version();

-- ── Backfill existing rows ───────────────────────────────────────────────
-- Each UPDATE re-fires the row's BEFORE trigger, populating search_vector
-- from the current version table. Runs once at migration time; idempotent
-- because the trigger always computes the vector from current data.
UPDATE elements    SET current_version = current_version;
UPDATE diagrams    SET current_version = current_version;
UPDATE packages    SET current_version = current_version;
UPDATE sets        SET name = name;
UPDATE collections SET name = name;
