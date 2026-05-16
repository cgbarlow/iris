# Protocols

These protocols must be followed when using plan mode. They are non-negotiable.

## 1. Architecture Decision Records (ADRs)

**Always create or update an ADR when a decision is made.**

- Every architectural, technical, or significant design decision must be captured as an ADR in `/docs/adrs/`
- ADRs follow the enhanced WH(Y) format as defined in [ADR-001](./adrs/ADR-001-Enhanced-ADR-Format.md)
- ADRs are immutable once approved — create a new ADR to supersede a previous one rather than modifying it
- Include rejected alternatives and the rationale for rejecting them
- Track dependencies between ADRs

## 2. Specifications

**Always create or update a spec that links/references an ADR or ADRs.**

- Every ADR that involves implementation details must have a corresponding specification in `/docs/adrs/specs/`
- Specs are the living documents — they evolve with the implementation
- ADRs remain stable decision records; specs capture the "how"
- Spec filenames follow the pattern: `SPEC-{ADR-number}-{letter}-{Title}.md`
- Each spec must reference the ADR(s) it implements

## 3. Test-Driven Development (TDD)

**Always follow TDD.**

- Write tests before writing implementation code
- Red → Green → Refactor cycle for every feature and bug fix
- Tests must cover the acceptance criteria defined in the relevant spec
- No code is merged without passing tests
- Test coverage must not decrease with any change

## 4. Feature Branches

**Always create a new feature branch for any changes.**

- Branch from `main` for every change, no matter how small
- Branch naming convention: `feature/{description}`, `fix/{description}`, `docs/{description}`
- No direct commits to `main`
- Each branch corresponds to a single logical change
- Clean up branches after merge

## 5. Changelog

**Maintain a changelog with versions.**

- Maintain `CHANGELOG.md` in the project root following [Keep a Changelog](https://keepachangelog.com/) format
- Every user-facing change must be recorded under the appropriate category (Added, Changed, Deprecated, Removed, Fixed, Security)
- Unreleased changes go under an `[Unreleased]` heading
- Version numbers follow [Semantic Versioning](https://semver.org/)

## 6. Releases

**Release versions as appropriate when changes are made.**

- Tag releases with semantic version numbers
- Move unreleased changelog entries to the new version heading
- Each release must pass all tests and quality checks
- Release notes reference the relevant ADRs and specs

## 7. Frontend Security — `{@html}` Protocol

**Never use Svelte's `{@html}` directive without DOMPurify sanitisation.**

- Svelte escapes HTML by default in `{expressions}` — this is the safe default
- `{@html}` renders raw HTML and bypasses Svelte's escaping — this is a stored XSS vector
- Any use of `{@html}` must pass content through DOMPurify (or equivalent sanitisation library) before rendering
- This applies to all user-generated content: entity names, descriptions, comments, model metadata, search results
- Code review must flag any `{@html}` usage without a corresponding sanitisation call
- Content Security Policy (CSP) headers must be configured to block inline script execution as a defence-in-depth measure
- This protocol addresses NZISM control 14.5.6.C.01 (web content security) and 14.5.8.C.01 (web application security)

## 8. Context7 MCP for Language Research

**Use the Context7 MCP to research appropriate language syntax and usage.**

- Before writing code in an unfamiliar library, framework, or API, use the Context7 MCP to fetch current documentation
- Append "use context7" to prompts when you need up-to-date syntax, API signatures, or usage patterns
- This ensures code follows the latest conventions and avoids deprecated patterns
- Applies to all technology in the stack: SvelteKit/Svelte 5, Svelte Flow, shadcn-svelte, Tailwind CSS, FastAPI, SQLite, pytest, and any other library used in Iris

## 9. Production-Ready Code Only

**No mocks, stubs, or placeholder implementations. Only fully working production-ready code.**

- Every line of code written must be real, functional, and production-ready
- No mock implementations, fake data layers, placeholder functions, or "TODO: implement later" stubs
- If a dependency is not yet built, wait for it — do not mock it
- Tests use proper test fixtures and factories, not mocks of the system under test
- External dependencies (e.g., database, filesystem) may use test doubles in tests only — never in application code
- If something cannot be fully implemented yet, do not write it at all — defer it to the appropriate phase

## 10. Claude Agent Teams

**Use Claude agent teams where suitable to get work done efficiently.**

- When tasks can be parallelised, use Claude sub-agents (Task tool) to work on independent items concurrently
- Use specialised agents (Explore, Plan, general-purpose) matched to the task type
- Research and exploration tasks should use Explore agents to avoid polluting the main context window
- Independent code changes across different files or modules can be delegated to parallel agents working in isolated worktrees
- Agent results should be verified before integration — trust but verify

## 11. Latest Stable Dependencies

**Always check for the latest available stable dependency and use that.**

- When adding any new dependency to the project (backend or frontend), check for the latest stable release before installing
- Do not assume pinned versions from documentation or examples are current — verify against the package registry (PyPI, npm)
- Use stable releases only — no alpha, beta, release candidate, or pre-release versions unless explicitly approved
- When updating existing dependencies, prefer the latest stable version compatible with the project's constraints
- Document the version chosen and the date it was verified in the relevant commit message

## 12. README Accuracy

**The README must be kept up to date and must accurately reflect the implementation.**

- Every feature described in the README must exist in the codebase — no aspirational claims
- When a feature is added, changed, or removed, update the README in the same branch
- Technical descriptions (algorithms, libraries, architecture) must match the actual implementation
- If a capability is planned but not yet implemented, it must not appear in the README
- README review is part of every release checklist

## 13. Don't Repeat Yourself (DRY)

**Eliminate duplication — every piece of knowledge must have a single, authoritative representation.**

- Before writing new code, check for existing implementations that solve the same problem — reuse rather than duplicate
- Extract shared logic into functions, utilities, or modules when the same pattern appears in more than one place
- Shared constants, types, and configuration values must be defined once and imported everywhere they are used
- When fixing a bug or changing behaviour, identify all locations where the same logic exists — fix them all or extract the common code
- Components with identical or near-identical structure should be refactored into a single parameterised component
- Backend and frontend must not independently re-implement the same validation rules — share the source of truth or derive one from the other
- Test helpers and fixtures used across multiple test files must live in shared modules, not be copy-pasted
- Duplication in ADRs and specs is acceptable — documentation may restate for clarity, but code must not

## 14. Surface Parity (v6.6.0)

**Every backend write endpoint MUST have a matching MCP tool AND a matching CLI subcommand.**

- Write endpoints are `POST` / `PUT` / `PATCH` / `DELETE` on a domain entity. Read endpoints (`GET`) are out of scope — different surfaces have different read affordances, and matching them rigidly would over-constrain.
- Enforced by `scripts/check_surface_parity.py`, which runs in CI on every PR that touches a router, the MCP tools file, the CLI main file, or the script itself. Hard-fails on a write-parity diff.
- Documented asymmetries (CLI `ask`, no `delete_*`, no `move_element`, no cross-set moves) are codified in the script's exception list. New asymmetries need a corresponding ADR and the script update.
- DRY corollary (§13): the md → docx and md → pdf renderers exist only in `backend/app/export/renderers/`. The script also checks this — no other module may import `weasyprint` or `markdown_it` for rendering.
- See [ADR-182](./adrs/ADR-182-Surface-Parity-Discipline.md) for the full rationale and the exception catalogue.

## 15. SQLite ↔ Supabase Migration Parity

**Every database change must work on both SQLite and Supabase (PostgreSQL) deployments. Passing tests on SQLite is not sufficient.**

- Every SQLite migration in `backend/app/migrations/m{NNN}_*.py` must ship in the same PR as its Supabase mirror in `backend/app/migrations/supabase/m{NNN}_*.sql`. Numbering is independent per family — link the pair in the SQL header (`-- Mirrors SQLite m{NNN}.`) so reviewers can pair them at a glance.
- Both halves must be idempotent: SQLite via `IF NOT EXISTS` / `INSERT OR IGNORE`; Supabase via `IF NOT EXISTS` and `ON CONFLICT ... DO NOTHING`. Migrations may be re-run.
- Boolean columns: PostgreSQL rejects integer literals where a `BOOLEAN` is expected. Supabase migrations MUST use `TRUE`/`FALSE`, even when the SQLite mirror uses `0`/`1`. This is the most common slip — see the v5.12.x regression guards in `backend/tests/test_migrations/test_response_format_prompts_schema.py` and the m069 / issue #152 incident.
- Row access in service code: asyncpg returns native `datetime` / `UUID` objects (normalised to strings by `_normalize_row` in `backend/app/db/adapter.py`) wrapped in plain tuples; aiosqlite returns `Row` objects that support string-key access. Service-layer code MUST read rows positionally (`r[0]`, `r[1]`, …) — `row["col"]` works on SQLite and 500s on Supabase. The export-service incident (v6.6.5) is the cautionary tale.
- Dollar-quoted SQL (`$$ … $$`), trigger and function definitions cannot be executed by asyncpg at startup. They live only in the Supabase `.sql` files and are applied via `scripts/supabase-migrate.sh`; the Supabase startup path in `backend/app/startup.py:_initialize_supabase` deliberately does NOT run the migration runner.
- **Release ordering for Supabase deployments**: schema-dependent code MUST NOT go live before its column exists. The release checklist for any version that adds a Supabase migration must include applying the migration BEFORE rolling the app forward. Render auto-deploys on push, so the safe sequence is: (a) merge migration-only PR, (b) run `scripts/supabase-migrate.sh` against the target DB, (c) merge the code change that depends on the new schema.
- Every new migration ships with a per-migration schema test in `backend/tests/test_migrations/` that asserts the boolean-literal convention, idempotency markers, and any cross-mode constraints. Copy the pattern from `test_response_format_prompts_schema.py` / `test_cascade_ux_polish_schema.py`.
