# SPEC-084-A: EAP-to-SQLite Conversion Pipeline

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-084-A |
| **ADR** | [ADR-084](../ADR-084-EAP-File-Import.md) |
| **Status** | Implemented |

## Module

```
backend/app/import_sparx/eap_converter.py
```

## JET4 Detection

The first 20 bytes of a JET 4.0 (MDB) file contain:

```
\x00\x01\x00\x00Standard Jet DB
```

The `is_jet4_file(path)` function reads these bytes and returns `True` if the signature matches.

## Conversion Process

`convert_eap_to_sqlite(eap_path) -> str`:

1. **Prerequisite check**: Verify `mdb-tables` is on PATH via `shutil.which`; raise `RuntimeError` if missing
2. **Format check**: Verify file is JET4 via `is_jet4_file`; raise `ValueError` if not
3. **Create temp SQLite**: `tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)`
4. **For each required table** (`t_package`, `t_object`, `t_connector`, `t_diagram`, `t_diagramobjects`, `t_attribute`, `t_objectproperties`):
   a. Run `mdb-schema <eap_path> <table> sqlite` to get CREATE TABLE DDL
   b. Run `mdb-export -I sqlite <eap_path> <table>` to get INSERT statements
   c. Execute DDL and INSERTs against temp SQLite via `aiosqlite`
5. **Return** path to temp SQLite file; caller is responsible for cleanup

## Required Tables

| Table | Purpose |
|-------|---------|
| `t_package` | Package hierarchy |
| `t_object` | Elements/objects |
| `t_connector` | Relationships |
| `t_diagram` | Diagram definitions |
| `t_diagramobjects` | Element positions on diagrams |
| `t_attribute` | Class attributes |
| `t_objectproperties` | Tagged values |

Tables missing from the MDB file are skipped with a logged warning (some older EAP files may lack `t_objectproperties`).

## Router Changes

`POST /api/import/sparx` accepts both `.qea` and `.eap` extensions:
- `.qea`: passes directly to `import_sparx_file()` (existing behaviour)
- `.eap`: calls `convert_eap_to_sqlite()` first, passes result to `import_sparx_file()`, cleans up both temp files

## Error Handling

| Condition | Response |
|-----------|----------|
| `mdbtools` not installed | `RuntimeError("mdbtools is not installed...")` |
| File is not JET4 format | `ValueError("File is not a JET4 (MDB) file")` |
| Table missing from MDB | Warning logged, table skipped |
| `mdb-schema`/`mdb-export` fails | `RuntimeError` with stderr output |

## Frontend Changes

- File picker accepts both `.qea` and `.eap` extensions
- Labels updated: "SparxEA files (.qea, .eap)"
- No new components or state required
