# ADR-084: EAP File Import

## Status
Accepted

## Date
2026-03-05

## What
Add support for importing Sparx EA `.eap` (JET 4.0 / MS Access / MDB) files alongside existing `.qea` (SQLite) import.

## Why
The `.eap` format is used by Sparx EA versions prior to EA 16. Many organisations still have repositories in this older format and need to import them into Iris without manual conversion. The `.eap` and `.qea` files share the identical table schema (`t_package`, `t_object`, `t_connector`, `t_diagram`, `t_diagramobjects`, `t_attribute`, `t_objectproperties`), so the existing import pipeline can be reused entirely after converting the MDB file to SQLite.

## How
1. Add an `eap_converter.py` module that converts `.eap` (MDB) files to temporary SQLite databases using the `mdbtools` CLI (`mdb-schema` for DDL, `mdb-export -I sqlite` for INSERT statements)
2. Detect JET 4.0 format by checking the file's first 20 bytes for the JET4 magic signature
3. For `.eap` uploads: convert to SQLite, then pass through the existing reader/mapper/converter/service pipeline unchanged
4. Update the router to accept both `.qea` and `.eap` extensions
5. Update the frontend to accept both file types
6. Require `mdbtools` as a system dependency (provides `mdb-tables`, `mdb-schema`, `mdb-export`)

## Alternatives Considered
- **Pure Python MDB parsing**: No mature async-compatible library exists; `mdbtools` is the de facto standard
- **Require users to convert manually**: Poor UX, adds friction for pre-EA 16 users
- **Use ODBC bridge**: Heavy dependency, platform-specific, harder to deploy

## Consequences
- `.eap` files are now supported with zero changes to the core import pipeline
- `mdbtools` becomes a required system package for `.eap` import (graceful error if missing)
- Temporary SQLite files are created during conversion and cleaned up after import
- No schema changes or database migrations required
