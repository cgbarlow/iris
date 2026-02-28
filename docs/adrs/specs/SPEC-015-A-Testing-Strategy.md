# SPEC-015-A: Testing Strategy Specification

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-015-A |
| **ADR Reference** | [ADR-015: Testing Strategy](../ADR-015-Testing-Strategy.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the testing strategy for the Iris project. It provides concrete selection criteria, Gherkin authoring conventions, file structure standards, test infrastructure configuration, and the decision flowchart that contributors follow when writing tests.

---

## 1. Test Layer Selection Criteria

### 1.1 Backend pytest

| Write a backend test when... | Example |
|------------------------------|---------|
| Testing an API endpoint's behaviour | `POST /api/entities` returns 201 with valid payload |
| Testing database constraints or queries | Unique name constraint raises 409 |
| Testing service-layer logic | Argon2id hashing, JWT generation, RBAC checks |
| Testing audit log creation | Middleware writes audit entry on entity mutation |
| Testing rate limiting | Login endpoint returns 429 after threshold |
| Testing search | FTS5 query returns ranked results |
| Testing entity versioning | Revert creates new version, not overwrite |

**Do not use backend pytest for:** Browser rendering, CSS, DOM assertions, or UI workflows.

### 1.2 Vitest Unit Tests

| Write a Vitest test when... | Example |
|-----------------------------|---------|
| Testing a pure function | `apiFetch<T>()` handles 401 by redirecting to login |
| Testing a data transformation | Canvas node layout calculation |
| Testing a type registry | `simpleViewNodeTypes` maps `'Component'` to correct component |
| Testing input sanitisation logic | DOMPurify strips `<script>` tags |
| Testing compliance rules | WCAG contrast ratio calculations, NZISM password rules |
| Testing canvas data structures | Sequence diagram message parsing, edge routing |

**Do not use Vitest for:** Tests that require a running browser, real API calls, or multi-component UI flows.

### 1.3 Playwright E2E

| Write a Playwright E2E test when... | Example |
|--------------------------------------|---------|
| Testing auth flow mechanics | Login redirects to dashboard, invalid creds show error |
| Testing accessibility infrastructure | ARIA labels present, focus order correct, skip links work |
| Testing theming application | Dark mode applies correct CSS custom properties |
| Testing error states | 404 page renders, network errors show alert |
| Testing admin tools | User management table loads, audit log filters work |
| Testing navigation structure | Sidebar links, breadcrumbs, URL routing |

**Do not use Playwright E2E for:** User-facing workflows that map to acceptance criteria in specs — use Gherkin BDD instead.

### 1.4 playwright-bdd Gherkin

| Write a Gherkin BDD test when... | Example |
|----------------------------------|---------|
| Testing a CRUD workflow | Creating, editing, deleting an entity via the UI |
| Testing canvas interactions | Adding a node, connecting entities, browse mode |
| Testing a feature with spec acceptance criteria | SPEC-011-A canvas interactions, SPEC-012-A gallery view |
| Testing a multi-step user journey | Model → Canvas tab → Add entity → Save → Reload → Verify |
| Testing keyboard-driven canvas workflows | Tab navigation, arrow key movement, Delete key |
| Testing business rules through the UI | Bookmarking a model, adding comments, password change |

**Do not use Gherkin for:** CSS assertions, ARIA attribute checks, error handling mechanics, or single-assertion validations.

---

## 2. Decision Flowchart

```
┌─────────────────────────────────────────┐
│ What are you testing?                   │
└───────────┬─────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│ Is it backend logic?                    │
│ (API, DB, service, middleware)          │
│                                         │
│  YES → pytest (backend/tests/)          │
└───────────┬─────────────────────────────┘
            │ NO
            ▼
┌─────────────────────────────────────────┐
│ Is it frontend logic testable without   │
│ a browser?                              │
│ (pure function, data transform, type    │
│  registry, validation rule)             │
│                                         │
│  YES → Vitest (tests/unit/)             │
└───────────┬─────────────────────────────┘
            │ NO
            ▼
┌─────────────────────────────────────────┐
│ Is it a user-facing workflow that maps  │
│ to spec acceptance criteria?            │
│                                         │
│ Could a stakeholder read the scenario   │
│ and confirm it matches their intent?    │
│                                         │
│  YES → Gherkin BDD (tests/bdd/)        │
└───────────┬─────────────────────────────┘
            │ NO
            ▼
┌─────────────────────────────────────────┐
│ It is a technical integration concern   │
│ (auth mechanics, a11y attributes, CSS,  │
│  error states, admin tools, navigation) │
│                                         │
│  → Playwright E2E (tests/e2e/)          │
└─────────────────────────────────────────┘
```

---

## 3. Gherkin Authoring Conventions

### 3.1 When to Write Gherkin

A scenario belongs in a `.feature` file when **all four** of these apply:

1. **Stakeholder-readable** — A product owner or architect could read it and confirm correctness
2. **Behaviour-focused** — Describes *what* the user does and observes, not *how* the UI is wired
3. **Spec-traceable** — Maps to an acceptance criterion in a SPEC document
4. **Multi-step** — Involves a meaningful sequence of actions (not a single assertion)

### 3.2 When NOT to Write Gherkin

| Situation | Use Instead |
|-----------|-------------|
| Asserting a CSS class or custom property value | Playwright E2E |
| Checking an ARIA attribute exists | Playwright E2E |
| Testing token refresh or 401 redirect | Playwright E2E |
| Testing a race condition or timeout | Playwright E2E |
| Verifying a single function's return value | Vitest |
| Scenario would be a trivial Given/When/Then with no reuse | Playwright E2E |

### 3.3 Feature File Standards

- **One feature per file.** Feature name matches the file name: `entity-crud.feature` → `Feature: Entity CRUD`
- **Background for shared setup.** Login and navigation that every scenario needs goes in `Background:`
- **Scenarios are independent.** Each scenario must work in isolation — no reliance on ordering
- **Use domain language.** Step text uses the language of the user, not implementation details
- **Parameterise with examples.** Use `Scenario Outline` + `Examples` when testing the same flow with different data

### 3.4 Step Definition Standards

- **Step files live in `tests/bdd/steps/`.** Organised by domain, not by feature file
- **Reuse steps across features.** Generic steps (login, navigation) are shared; domain steps (canvas, entity) are co-located by domain
- **API-first seeding.** `Given` steps create data via API calls, not UI interactions
- **Assertions use Playwright locators.** `Then` steps use `expect(locator)` with accessibility-first selectors (`getByRole`, `getByLabel`)
- **Avoid brittle selectors.** Prefer `getByRole('button', { name: 'Create' })` over `locator('.btn-primary')`

### 3.5 Example: Good vs Bad Gherkin

**Good** — behaviour-focused, stakeholder-readable:
```gherkin
Scenario: Adding a component entity to the canvas
  When I navigate to model "Test Architecture"
  And I click the "Canvas" tab
  And I click "Start Building"
  And I click "Add Entity"
  And I fill in entity name "Payment Service"
  And I select entity type "Component"
  And I click "Create"
  Then a node labelled "Payment Service" should appear on the canvas
```

**Bad** — implementation-focused, not stakeholder-readable:
```gherkin
Scenario: Adding a component entity to the canvas
  When I navigate to "/models/1"
  And I click "[data-testid=canvas-tab]"
  And I click "[data-testid=start-building-btn]"
  And I click "[data-testid=add-entity-btn]"
  And I fill "#entity-name-input" with "Payment Service"
  And I select "#entity-type-select" value "component"
  And I click "[data-testid=create-btn]"
  Then ".svelte-flow .react-flow__node" should contain text "Payment Service"
```

---

## 4. File Structure

```
iris/
├── backend/
│   └── tests/                          # Backend pytest
│       ├── conftest.py                 # Shared fixtures (async client, DB)
│       ├── test_auth/                  # Auth domain tests
│       ├── test_entities/              # Entity CRUD + stats tests
│       ├── test_models/                # Model CRUD tests
│       ├── test_relationships/         # Relationship CRUD tests
│       ├── test_audit/                 # Audit log tests
│       ├── test_users/                 # User management tests
│       ├── test_comments/              # Comment route tests
│       ├── test_bookmarks/             # Bookmark route tests
│       ├── test_search/                # Search route tests
│       ├── test_database.py            # Database setup + PRAGMA tests
│       ├── test_rate_limit.py          # Rate limiting tests
│       └── test_startup.py             # App startup tests
│
└── frontend/
    ├── tests/
    │   ├── unit/                        # Vitest unit tests
    │   │   ├── api.test.ts
    │   │   ├── auth.test.ts
    │   │   ├── canvas.test.ts
    │   │   ├── sequence.test.ts
    │   │   ├── wcag.test.ts
    │   │   └── ...
    │   ├── e2e/                          # Playwright E2E tests
    │   │   ├── fixtures.ts               # Shared helpers (seedAdmin, loginAsAdmin)
    │   │   ├── auth.spec.ts
    │   │   ├── accessibility.spec.ts
    │   │   ├── theming.spec.ts
    │   │   └── ...
    │   └── bdd/                          # playwright-bdd Gherkin tests
    │       ├── features/                 # .feature files
    │       │   ├── entity-crud.feature
    │       │   ├── canvas-simple-view.feature
    │       │   ├── canvas-keyboard.feature
    │       │   ├── models-gallery.feature
    │       │   └── ...
    │       ├── steps/                    # Step definitions
    │       │   └── *.ts
    │       └── fixtures.ts               # BDD fixture extensions
    ├── .features-gen/                    # Generated by bddgen (gitignored)
    ├── playwright.config.ts              # Dual-project config (e2e + bdd)
    └── vite.config.ts                    # Vitest config (test.include)
```

---

## 5. Test Infrastructure

### 5.1 Playwright Configuration

```typescript
// playwright.config.ts — key settings
{
  timeout: 30_000,          // 30s per test
  retries: 1,               // handles cold-start flakiness
  workers: 1,               // sequential — shared SQLite DB
  use: {
    baseURL: 'http://localhost:4173',
    actionTimeout: 10_000,
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'e2e',  testDir: 'tests/e2e' },
    { name: 'bdd',  testDir: bddTestDir },  // .features-gen/
  ],
}
```

### 5.2 Backend Test Startup

`scripts/start-test-backend.sh` performs:

1. Kill any existing backend process on port 8000
2. Remove stale test database
3. Set elevated rate limits (`IRIS_RATE_LIMIT_LOGIN=200`, etc.)
4. Start backend with `uv run python -m app.main`

### 5.3 Vitest Configuration

```typescript
// vite.config.ts — test section
{
  test: {
    include: ['tests/unit/**/*.test.ts'],
    environment: 'jsdom',
  },
}
```

### 5.4 Backend pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

---

## 6. Test Data Strategy

| Concern | Approach |
|---------|----------|
| **Backend** | In-memory async test client with fresh DB per test module (`conftest.py`) |
| **Vitest** | Pure function inputs — no external state needed |
| **E2E** | `seedAdmin()` in `beforeAll`, API calls in test body |
| **BDD** | API-first seeding in `Given` steps via shared fixtures |
| **Isolation** | Each BDD scenario creates its own model/entities — no cross-test state |
| **Cleanup** | Not required — database is fresh per test run (backend script deletes stale DB) |

---

## 7. Coverage by Domain

This table maps each application domain to the test layers that cover it:

| Domain | pytest | Vitest | E2E | BDD |
|--------|--------|--------|-----|-----|
| Auth (login, JWT, refresh) | X | X | X | |
| RBAC (roles, permissions) | X | | | |
| Entities (CRUD) | X | | | X |
| Models (CRUD) | X | | X | X |
| Relationships | X | | | X |
| Canvas (simple, component) | | X | | X |
| Canvas (sequence) | | X | | X |
| Canvas (UML, ArchiMate) | | X | | X |
| Canvas (keyboard) | | | | X |
| Canvas (browse mode) | | | | X |
| Canvas (theming) | | | | X |
| Bookmarks | X | | | X |
| Comments | X | | | X |
| Search | X | | | |
| Audit log | X | | X | |
| User management | X | | X | |
| Accessibility | | X | X | |
| Theming (CSS) | | | X | |
| Navigation | | | X | |
| Error handling | | | X | |
| Gallery view | | | | X |
| Password change | | | | X |

---

## 8. Naming Conventions

| Layer | File Pattern | Example |
|-------|-------------|---------|
| Backend pytest | `test_{domain}/test_{concern}.py` | `test_auth/test_routes.py` |
| Vitest | `{domain}.test.ts` | `canvas.test.ts` |
| Playwright E2E | `{domain}.spec.ts` | `auth.spec.ts` |
| Gherkin features | `{domain}-{concern}.feature` | `canvas-simple-view.feature` |
| BDD steps | `{domain}.steps.ts` | `canvas.steps.ts` |

---

## 9. Running Tests

| Scope | Command | Working Directory |
|-------|---------|-------------------|
| All backend | `uv run python -m pytest` | `backend/` |
| All frontend unit | `npm test` | `frontend/` |
| All E2E (scripted) | `npm run test:e2e` | `frontend/` |
| All BDD | `npm run test:bdd` | `frontend/` |
| All E2E + BDD | `npm run test:all-e2e` | `frontend/` |
| Single E2E file | `npx playwright test --project=e2e tests/e2e/auth.spec.ts` | `frontend/` |
| Single BDD feature | `npx playwright test --project=bdd --grep "Entity CRUD"` | `frontend/` |

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Every new feature has tests at the appropriate layer(s) | Code review checks layer selection against this spec |
| Gherkin scenarios are stakeholder-readable | No CSS selectors, test IDs, or implementation details in step text |
| BDD step definitions use API-first seeding | `Given` steps call API helpers, not UI interactions |
| Test coverage does not decrease | CI reports coverage delta on each PR |
| All four test suites pass before merge | CI runs all layers in sequence |

---

*This specification implements [ADR-015](../ADR-015-Testing-Strategy.md).*
