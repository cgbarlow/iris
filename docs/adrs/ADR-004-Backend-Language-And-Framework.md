# ADR-004: Backend Language and Framework Selection

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-004 |
| **Initiative** | Iris Backend Tech Stack |
| **Proposed By** | The Architect (Bear) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** selecting a backend language and framework for Iris, which must serve a REST API for an interactive architectural modelling tool with authentication, RBAC, audit trails, version control operations, semantic search, and a carefully designed SQLite schema where entities are first-class objects with identity and relationships,

**facing** the trade-off between rapid development velocity (Python), full-stack language coherence (TypeScript/Node), maximum runtime performance and memory safety (Rust), and simplicity with strong concurrency (Go), for a small team of 2-5 prioritising development speed,

**we decided for** Python with FastAPI as the backend framework, giving direct control over the SQLite schema without ORM interference, async-first API performance, auto-generated OpenAPI documentation for typed Svelte client generation, and the richest ecosystem for rapid web API development,

**and neglected** Django + Django REST Framework (which provides batteries-included auth, ORM, admin panel, and RBAC but imposes an ORM model that conflicts with Iris's repository-first entity schema design, requiring workarounds rather than direct schema control), TypeScript/Node with Fastify or Hono (which offers full-stack language coherence with the SvelteKit frontend but has a less mature ecosystem for the specific backend requirements of auth, RBAC, search, and version control compared to Python), Rust with Axum or Actix (which offers the best runtime performance and memory safety but at a significantly steeper learning curve that conflicts with the rapid development priority), and Go with standard library or Gin (which offers excellent API performance and simplicity but a smaller web framework ecosystem than Python for auth, search, and database tooling),

**to achieve** rapid development velocity with the richest ecosystem for web APIs, full control over the SQLite schema design critical to the repository-first architecture, auto-generated API documentation enabling typed client generation for the Svelte frontend, lightweight async middleware for audit trailing without ORM magic hiding mutations, and easy integration with semantic search libraries (sqlite-vss, sentence-transformers),

**accepting that** the frontend (SvelteKit/TypeScript) and backend (Python) use different languages, requiring an API contract boundary rather than shared types; that Python's runtime performance is lower than Rust or Go (acceptable for this workload); and that the team must maintain proficiency in both TypeScript and Python.

---

## Options Considered

### Option 1: Python + FastAPI (Selected)

| Aspect | Detail |
|--------|--------|
| **Language** | Python 3.12+ |
| **Framework** | FastAPI |
| **ORM/DB** | SQLAlchemy or raw SQLite with custom schema |
| **Auth** | FastAPI security utilities + bcrypt/argon2 |
| **Search** | sqlite-vss or sentence-transformers |
| **API Docs** | Auto-generated OpenAPI (Swagger/ReDoc) |

**Pros:**
- Richest ecosystem for rapid web API development
- FastAPI is async-first with excellent performance for Python
- Auto-generated OpenAPI spec enables typed client generation for Svelte frontend
- Direct SQLite schema control — no ORM fighting the repository-first entity model
- Lightweight middleware for audit trails without hidden mutations
- Excellent libraries for semantic search (sqlite-vss, sentence-transformers, FAISS)
- Largest developer talent pool of any language
- Strong testing ecosystem (pytest, httpx for async testing)

**Cons:**
- Different language from frontend (TypeScript) — no shared types
- Python runtime performance lower than Rust/Go (acceptable for this workload)
- GIL limits true parallelism (mitigated by async I/O for API workloads)

### Option 2: Django + Django REST Framework (Rejected)

**Pros:**
- Batteries included: built-in ORM, auth, admin panel, permissions, CSRF
- Django REST Framework provides serialisation, viewsets, permissions out of the box
- Mature, well-documented, battle-tested at scale

**Cons:**
- Django's ORM wants to own the database schema — conflicts with Iris's carefully designed repository-first entity model
- Built-in auth/permissions model may not map cleanly to Iris's RBAC requirements
- Heavier framework with more ceremony for what is fundamentally a custom API
- Would spend time working *around* Django rather than *with* it

**Why rejected:** Django's opinionated ORM conflicts with the repository-first architecture (ADR-003). Iris needs precise control over the SQLite schema where entities have identity, versioning, and relationship semantics. Django's ORM would abstract away the very details that make Iris a repository rather than a CRUD application.

### Option 3: TypeScript/Node + Fastify (Rejected)

**Pros:**
- Same language as frontend — potential for shared types and validation schemas
- Single language proficiency for the team
- Fastify is performant and well-designed
- Strong TypeScript ecosystem

**Cons:**
- Less mature ecosystem for auth, RBAC, and search compared to Python
- SQLite bindings (better-sqlite3) are good but ecosystem is smaller
- Semantic search libraries less mature in Node than Python
- Full-stack TypeScript coherence is appealing but less important than having the best backend tooling

**Why rejected:** While full-stack coherence is attractive, Python's ecosystem for the specific backend requirements (auth, RBAC, semantic search, database tooling) is significantly richer. The API contract boundary between frontend and backend is well-served by auto-generated OpenAPI specs.

### Option 4: Rust + Axum (Rejected)

**Pros:**
- Best runtime performance and memory safety
- Excellent SQLite bindings (rusqlite)
- Growing web ecosystem (Axum, Tower)
- Strong type system prevents entire classes of bugs

**Cons:**
- Steepest learning curve of all options
- Slower development velocity — conflicts with rapid development priority
- Smaller web framework ecosystem (auth, search, middleware)
- Harder to hire Rust developers for a small team

**Why rejected:** The rapid development priority makes Rust's steep learning curve and slower iteration speed a poor fit. The performance advantages are not needed for this workload — API response times are dominated by database I/O, not compute.

### Option 5: Go + Standard Library/Gin (Rejected)

**Pros:**
- Excellent API performance
- Simple language, fast compilation
- Good concurrency model
- Strong standard library for HTTP

**Cons:**
- Smaller web framework ecosystem than Python for auth, search, database tooling
- Less expressive type system than TypeScript or Rust
- Semantic search library ecosystem much smaller than Python
- Error handling verbosity

**Why rejected:** Go's web ecosystem, while growing, is not as rich as Python's for the specific requirements of Iris (auth, RBAC, semantic search, audit trails). The simplicity advantage does not outweigh Python's ecosystem depth for this use case.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Proceed with Python/FastAPI | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The Architect (Bear) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-003 | Architectural Vision | Repository-first architecture requires direct schema control |
| Relates To | ADR-002 | Frontend Tech Stack | API contract boundary between Python backend and SvelteKit frontend |
| Enables | TBD | Data Foundation Schema Design | FastAPI + SQLite is the implementation foundation for Phase A |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-004-A | Backend Stack Configuration | Technical Specification | specs/SPEC-004-A-Backend-Stack.md (TBD) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
