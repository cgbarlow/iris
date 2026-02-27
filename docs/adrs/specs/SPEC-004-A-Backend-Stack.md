# SPEC-004-A: Backend Stack Configuration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-004-A |
| **ADR Reference** | [ADR-004: Backend Language and Framework](../ADR-004-Backend-Language-And-Framework.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the backend stack configuration for Iris, implementing the decisions captured in ADR-004 (Python/FastAPI) with security requirements from ADR-005 (RBAC), ADR-007 (Audit Log Integrity), and the NZ ITSM Control Mapping.

---

## Python Configuration

| Component | Requirement |
|-----------|-------------|
| **Python Version** | 3.12+ |
| **Package Manager** | uv (preferred) or pip with requirements.txt |
| **Virtual Environment** | Required for all development and deployment |
| **Type Checking** | mypy with strict mode |
| **Linting** | ruff |
| **Formatting** | ruff format |
| **Testing** | pytest with pytest-asyncio for async tests |

---

## FastAPI Configuration

| Component | Requirement |
|-----------|-------------|
| **Framework Version** | FastAPI 0.110+ |
| **ASGI Server** | uvicorn |
| **API Documentation** | Auto-generated OpenAPI (enabled in development, disabled in production) |
| **Request Validation** | Pydantic v2 models for all request/response schemas |
| **Middleware** | CORS, audit logging, authentication, rate limiting |

---

## SQLite Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| **WAL Mode** | **MANDATORY** — `PRAGMA journal_mode=WAL` | Enables concurrent reads during writes. Non-negotiable per CISO risk assessment. Must be set on every database connection. |
| **Foreign Keys** | `PRAGMA foreign_keys=ON` | Enforces referential integrity. Must be set on every connection (SQLite does not enable this by default). |
| **Busy Timeout** | `PRAGMA busy_timeout=5000` | 5-second wait on locked database before returning SQLITE_BUSY. Prevents immediate failures under contention. |
| **Synchronous** | `PRAGMA synchronous=NORMAL` | Safe with WAL mode. Balances durability and performance. |
| **Cache Size** | `PRAGMA cache_size=-64000` | 64MB cache. Adjust based on deployment memory. |
| **Journal Size Limit** | `PRAGMA journal_size_limit=67108864` | 64MB WAL file limit. Triggers automatic checkpoint. |
| **Auto Vacuum** | `PRAGMA auto_vacuum=INCREMENTAL` | Reclaims space without full vacuum locks. |

### Database Files

| File | Purpose | WAL Mode | Hash Chain |
|------|---------|----------|------------|
| `data/iris.db` | Application database — entities, models, relationships, users, roles, permissions | Yes | No |
| `data/iris_audit.db` | Audit database — tamper-evident hash-chained audit log | Yes | Yes |

### Connection Management

- Use a connection pool (aiosqlite or similar async SQLite driver)
- Set all PRAGMAs on connection creation, not per-query
- Connection factory pattern to ensure consistent configuration
- Maximum 1 write connection per database file (SQLite constraint)
- Multiple read connections allowed with WAL mode

---

## Authentication Configuration

| Component | Requirement | Rationale |
|-----------|-------------|-----------|
| **Password Hashing** | **Argon2id** | Current OWASP and NIST recommendation. Resistant to GPU and side-channel attacks. NOT bcrypt — Argon2id is the superior choice for new applications. |
| **Argon2id Parameters** | `time_cost=3`, `memory_cost=65536` (64MB), `parallelism=4` | OWASP recommended minimum. Adjust based on server hardware. |
| **Python Library** | `argon2-cffi` | Reference implementation binding for Python |
| **Access Tokens** | Signed JWT, 15-minute expiry | Short-lived to limit exposure window |
| **Refresh Tokens** | Server-stored, 7-day expiry, rotation on use | Stored in database for revocation capability |
| **Token Signing** | HS256 with 256-bit secret (minimum) | Symmetric signing suitable for single-server deployment |
| **Rate Limiting** | 5 failed login attempts → 15-minute lockout per account | Brute force mitigation |
| **Password Complexity** | Minimum 12 characters, no maximum (up to 128), checked against common password list | NIST SP 800-63B alignment |

---

## Security Headers

All API responses must include:

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | Configured per deployment (see Phase D) |

---

## CORS Configuration

| Setting | Development | Production |
|---------|------------|------------|
| **Allowed Origins** | `http://localhost:5173` (SvelteKit dev server) | Deployment domain only |
| **Allowed Methods** | `GET, POST, PUT, DELETE, OPTIONS` | Same |
| **Allowed Headers** | `Authorization, Content-Type` | Same |
| **Credentials** | `true` | `true` |
| **Max Age** | `3600` | `3600` |

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application factory
│   ├── config.py             # Configuration management
│   ├── database.py           # SQLite connection management (PRAGMA configuration)
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── service.py        # Authentication logic (Argon2id)
│   │   ├── dependencies.py   # FastAPI dependencies (current_user, require_permission)
│   │   └── models.py         # Pydantic models for auth requests/responses
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── service.py        # Audit logging with hash chain
│   │   └── models.py         # Audit entry models
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── service.py        # Entity CRUD with versioning
│   │   ├── router.py         # API routes
│   │   └── models.py         # Pydantic models
│   ├── models/                # Architecture model management (not Pydantic models)
│   │   └── ...
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── audit.py          # Audit logging middleware
│   │   ├── auth.py           # Authentication middleware
│   │   └── rate_limit.py     # Rate limiting middleware
│   └── migrations/
│       └── ...               # Schema migration scripts
├── tests/
│   ├── conftest.py
│   ├── test_auth/
│   ├── test_entities/
│   ├── test_audit/
│   └── ...
├── data/                      # Database files (gitignored)
│   ├── iris.db
│   └── iris_audit.db
├── pyproject.toml
└── README.md
```

---

## Dependencies (Core)

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response validation |
| `aiosqlite` | Async SQLite driver |
| `argon2-cffi` | Password hashing (Argon2id) |
| `python-jose[cryptography]` | JWT token handling |
| `httpx` | HTTP client for testing |
| `pytest` | Testing framework |
| `pytest-asyncio` | Async test support |
| `ruff` | Linting and formatting |
| `mypy` | Type checking |

---

*This specification implements [ADR-004](../ADR-004-Backend-Language-And-Framework.md) and incorporates security requirements from [ADR-005](../ADR-005-RBAC-Design.md) and [ADR-007](../ADR-007-Audit-Log-Integrity.md).*
