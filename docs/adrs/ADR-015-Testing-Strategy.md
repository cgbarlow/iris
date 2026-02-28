# ADR-015: Testing Strategy

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-015 |
| **Initiative** | Testing Strategy |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris project, which has a Python/FastAPI backend, a SvelteKit/Svelte 5 frontend with interactive canvas editing, and compliance requirements (WCAG 2.2 AA, NZISM v3.9),

**facing** the need for a clear, documented strategy that defines when to use each of the project's four test layers (backend pytest, frontend Vitest unit, Playwright E2E, playwright-bdd Gherkin) so that contributors select the right test type for each situation and avoid gaps or duplication,

**we decided for** a four-layer testing pyramid with explicit selection criteria: backend pytest for API and data-layer logic, Vitest for frontend pure-logic units, Playwright E2E for technical integration flows, and playwright-bdd Gherkin for user-facing behaviour that benefits from business-readable specifications,

**and neglected** a single-layer strategy using only E2E tests (which would be slow and fragile), a single-layer strategy using only unit tests (which would miss integration issues), and collapsing BDD and E2E into one undifferentiated layer (which would lose the documentation value of Gherkin for stakeholder-facing behaviour),

**to achieve** fast feedback at the unit level, reliable integration coverage at the E2E level, living documentation of user-facing behaviour through Gherkin feature files, and a clear decision framework that eliminates ambiguity about which test type to write,

**accepting that** four test layers require contributors to understand the selection criteria, that Gherkin introduces a learning curve, and that maintaining step definitions adds overhead compared to plain Playwright tests.

---

## The Four Test Layers

| Layer | Framework | Location | Runs Via | Speed |
|-------|-----------|----------|----------|-------|
| **Backend** | pytest (async) | `backend/tests/` | `uv run python -m pytest` | Fast (~seconds) |
| **Frontend Unit** | Vitest + jsdom | `frontend/tests/unit/` | `npm test` | Fast (~seconds) |
| **E2E** | Playwright | `frontend/tests/e2e/` | `npm run test:e2e` | Slow (~minutes) |
| **BDD** | playwright-bdd | `frontend/tests/bdd/` | `npm run test:bdd` | Slow (~minutes) |

---

## When to Use Each Layer

### Backend pytest — API and data-layer logic

Write a backend test when the thing under test is:

- An API endpoint (route handler, request validation, response shape)
- A database operation (CRUD, migrations, constraints, FTS5 queries)
- A service-layer function (auth, RBAC, audit logging, versioning, search)
- Rate limiting, middleware, or startup behaviour
- Anything that does not require a browser

**Examples from codebase:** `test_auth/test_routes.py`, `test_entities/test_crud.py`, `test_audit/test_service.py`, `test_rate_limit.py`

### Vitest — Frontend pure-logic units

Write a Vitest test when the thing under test is:

- A utility function, data transformation, or computation (`apiFetch`, auth helpers)
- A type registry, node/edge type mapping, or configuration object
- Canvas data structures (node layout, edge routing, sequence diagram parsing)
- Compliance validation logic (WCAG contrast ratios, NZISM password rules)
- Any frontend logic that can be exercised without rendering a full page

**Examples from codebase:** `api.test.ts`, `canvas.test.ts`, `nodeTypeRegistry.test.ts`, `sequence.test.ts`, `wcag.test.ts`

### Playwright E2E — Technical integration flows

Write a standard Playwright E2E test when the thing under test is:

- A technical integration concern (auth flow, token refresh, error handling, navigation)
- An infrastructure-level UI behaviour (accessibility attributes, theming CSS, dashboard rendering)
- A flow where the *implementation mechanics* matter more than the *user story*
- Admin-facing functionality (user management, audit log viewer)

**Examples from codebase:** `auth.spec.ts`, `accessibility.spec.ts`, `theming.spec.ts`, `admin-audit.spec.ts`, `navigation.spec.ts`

### playwright-bdd Gherkin — User-facing behaviour specifications

Write a Gherkin BDD test when the thing under test is:

- A user-facing workflow that a stakeholder would recognise (CRUD, canvas editing, bookmarking)
- A behaviour that benefits from Given/When/Then readability as living documentation
- A canvas interaction (adding entities, connecting nodes, browse mode, keyboard shortcuts)
- A feature where the *acceptance criteria from a spec* map naturally to scenarios
- A flow that crosses multiple UI components in a single user journey

**Examples from codebase:** `entity-crud.feature`, `canvas-simple-view.feature`, `canvas-keyboard.feature`, `models-gallery.feature`, `bookmarks.feature`

---

## Decision Flowchart

```
Is it backend logic (API, DB, service)?
  YES → backend pytest
  NO  ↓

Is it frontend logic testable without a browser?
  YES → Vitest unit test
  NO  ↓

Is it a user-facing workflow that a stakeholder would read?
  YES → Gherkin BDD (.feature file)
  NO  ↓

It is a technical integration concern
      → Playwright E2E (.spec.ts)
```

---

## When to Write Gherkin (Detailed Guidance)

Gherkin is the right choice when **all** of these apply:

1. **Stakeholder-readable** — A product owner or architect could read the scenario and confirm it matches their intent
2. **Behaviour, not mechanics** — The scenario describes *what* the user does and *what* happens, not *how* the UI is wired
3. **Spec-traceable** — The scenario maps to an acceptance criterion in a spec (e.g., SPEC-011-A, SPEC-012-A)
4. **Multi-step user journey** — The scenario involves a meaningful sequence of actions, not a single assertion

Gherkin is the **wrong** choice when:

- The test asserts CSS values, ARIA attributes, or HTML structure (use Playwright E2E)
- The test checks error handling, token refresh, or race conditions (use Playwright E2E)
- The test verifies a single function's return value (use Vitest)
- The scenario would be a single Given/When/Then with no reusable steps

---

## Test Counts (Current)

| Layer | Test Count |
|-------|-----------|
| Backend pytest | 217 |
| Vitest unit | 148 |
| Playwright E2E | 41 |
| playwright-bdd | 42 |
| **Total** | **448** |

---

## Infrastructure Decisions

| Concern | Decision | Rationale |
|---------|----------|-----------|
| **Playwright workers** | 1 (sequential) | Shared SQLite database; parallel writes cause flakiness |
| **Retries** | 1 | Handles cold-start flakiness from webServer spin-up |
| **Trace** | On first retry | Captures debugging data without slowing green runs |
| **Test data seeding** | API-first in Given steps | Faster and more reliable than UI-driven setup |
| **BDD code generation** | `bddgen` before test run | `.features-gen/` is gitignored; regenerated each run |
| **Backend startup** | `scripts/start-test-backend.sh` | Kills stale processes, removes stale DB, elevates rate limits |
| **Database reset** | Not between tests | Tests must be independent via unique test data, not DB wipes |

---

## Options Considered

### Option 1: Four-Layer Pyramid with Explicit Selection Criteria (Selected)

**Pros:**
- Clear guidance eliminates ambiguity about which test type to write
- Fast feedback loop: most logic tested at unit level
- Gherkin provides living documentation for stakeholder-facing behaviour
- Each layer has a distinct purpose with minimal overlap

**Cons:**
- Contributors must learn four frameworks
- Gherkin step definitions require maintenance
- Selection criteria require judgement for edge cases

### Option 2: Two Layers Only — Unit + E2E (Rejected)

**Pros:**
- Simpler toolchain, fewer frameworks to learn
- No Gherkin learning curve

**Cons:**
- Loses business-readable executable specifications
- Canvas interactions poorly served by either pure unit or undifferentiated E2E
- No documentation value from tests

**Why rejected:** The canvas subsystem is complex enough that Gherkin scenarios provide significant clarity and serve as living documentation of acceptance criteria.

### Option 3: E2E-Only Strategy (Rejected)

**Pros:**
- Tests the full stack as users experience it
- Single framework to learn

**Cons:**
- Extremely slow feedback loop
- Brittle: UI changes break everything
- No isolation of logic bugs
- Cannot test backend independently

**Why rejected:** Violates the testing pyramid principle. Slow, expensive, and fragile.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Document and follow | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Vitest and Playwright choices follow from frontend stack |
| Depends On | ADR-004 | Backend Language and Framework | pytest follows from FastAPI/Python backend |
| Relates To | ADR-011 | Canvas Integration and Testing Strategy | ADR-011 introduced playwright-bdd; this ADR generalises the strategy across all layers |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-015-A | Testing Strategy Specification | Technical Specification | [specs/SPEC-015-A-Testing-Strategy.md](specs/SPEC-015-A-Testing-Strategy.md) |
| SPEC-011-D | Canvas BDD Test Plan | Technical Specification | [specs/SPEC-011-D-Canvas-BDD-Test-Plan.md](specs/SPEC-011-D-Canvas-BDD-Test-Plan.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
