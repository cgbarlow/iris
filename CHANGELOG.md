# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- North star document (`docs/north-star.md`)
- ADR framework cloned from cgbarlow/adr with enhanced WH(Y) format
- ADR-002: Frontend Technology Stack Selection (SvelteKit/Svelte 5)
- ADR-003: Architectural Vision — Repository First
- SPEC-002-A: Frontend Stack Configuration
- Development protocols (`docs/protocols.md`)
- ADR-004: Backend Language and Framework Selection (Python/FastAPI)
- SPEC-004-A: Backend Stack Configuration (SQLite WAL mode, Argon2id, project structure)
- ADR-005: RBAC Design (four-role permission-mapped model)
- SPEC-005-A: RBAC Permission Matrix
- SPEC-005-B: Authentication and Session Management
- ADR-006: Version Control and Rollback Semantics (immutable append-only, revert-as-new-version)
- SPEC-006-A: Entity Version Control Schema
- ADR-007: Audit Log Integrity (hash-chained, separate database)
- SPEC-007-A: Audit Log Schema and Hash Chain Implementation
- NZ ITSM Control Mapping (`docs/nz-itsm-control-mapping.md`) with specific NZISM v3.9 control references
- `{@html}` security protocol added to `docs/protocols.md`
- Context7 MCP research protocol added to `docs/protocols.md`
- ADR-008: Accessibility — WCAG 2.2 Compliance (Level AA + selected AAA)
- SPEC-008-A: WCAG 2.2 Compliance Matrix (58 criteria mapped to Iris)
- SPEC-003-A: Entity Domain Model (entity types, relationships, models, model placements, cross-reference queries)
- Campaign Mode setup with quest definition and guild profiles
- CHANGELOG.md
- Backend project skeleton with directory structure per SPEC-004-A
- `pyproject.toml` with uv, FastAPI, aiosqlite, argon2-cffi, python-jose, pytest, ruff, mypy
- `app/config.py` — configuration management with database, auth, and app settings
- `app/database.py` — SQLite connection factory with all 7 PRAGMAs (WAL, FK, busy_timeout, synchronous, cache_size, journal_size_limit, auto_vacuum)
- `tests/conftest.py` — shared test fixtures with real temp SQLite databases
- `.gitignore` for Python, Node, database, and IDE files
- `DatabaseManager` class for dual database connections (iris.db + iris_audit.db)
- Migration 001: roles, role_permissions, users, password_history, refresh_tokens tables per SPEC-005-A/B
- Migration 002: entities, entity_versions, relationships, relationship_versions, models, model_versions tables per SPEC-006-A/SPEC-003-A
- Migration 003: audit_log table with hash chain columns in separate audit database per SPEC-007-A
