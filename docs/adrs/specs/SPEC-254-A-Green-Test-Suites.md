# SPEC-254-A: Bring the Test Suites Back to Green

Implements **[ADR-254](../ADR-254-Green-Test-Suites.md)**. Issue [#307](https://github.com/cgbarlow/iris/issues/307).

## 1. Changes

| File | Change |
|------|--------|
| `backend/app/startup.py` | New `run_sqlite_main_migrations(main)` holding the ordered migration list; `_initialize_sqlite` calls it (no behaviour change). |
| `backend/app/import_sparx/eap_converter.py` | JET4 header check runs before the `mdbtools` check. |
| `backend/pyproject.toml` | `tmp_path_retention_policy = "failed"`. |
| `backend/tests/test_search/test_entity_indexing.py`, `test_rebuild.py`, `backend/tests/test_mnemos/test_dependencies.py` | Build their database with `run_sqlite_main_migrations`. |
| `backend/tests/test_import_sparx/test_eap_converter.py` | The missing-mdbtools test uses a file with a real JET4 header. |
| `backend/tests/test_startup.py` → `backend/tests/test_startup/test_initialize_databases.py` | Moved, so it is collected. |
| `frontend/tests/unit/{canvasTabFirst,extensionManagerFields,hierarchyControls,textViewTocToggle,umlRendering,viewsToolbarOrder}.test.ts` | Realigned with the current design; `umlRendering` now calls `nodeOverrideStyle` for both the authored and the EA fixed-size case. |
| `mcp/tests/test_create_element_tool.py`, `test_element_templates.py` | Schema assertions match v6.8.0 / ADR-211. |

## 2. Results (local, 2026-09-24)

| Suite | Before | After |
|---|---|---|
| Frontend vitest | 7 failed / 1314 passed | 1321 passed |
| MCP pytest | 2 failed / 286 passed | 288 passed |
| Backend pytest | 15 failed / 2202 passed (8 not collected) | all passed, including the 8 |
| CLI pytest | 70 passed once `cli/.venv` has editable installs of the local packages (environment only) | — |

## 3. Acceptance criteria

- Each suite passes on a clean checkout of this branch.
- A non-JET4 `.eap` upload returns 400 whether or not `mdbtools` is installed.
- A full backend run keeps no temp directories for passing tests.
