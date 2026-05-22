# ADR-214: Genericness invariant for the shopping-list workflow

Status: Accepted (2026-05-22)

Builds on: [ADR-210](./ADR-210-Smart-Markdown-Value-Overrides.md), [ADR-211](./ADR-211-Element-Template-Stamps.md), [ADR-212](./ADR-212-Aggregation-Profiles-And-Engine.md), [ADR-213](./ADR-213-Aggregation-List-Diagram-Type.md), [ADR-182](./ADR-182-Surface-Parity-Discipline.md).

## Context

The four primitives shipped in PRs 1–4 deliver the meal-plan → shopping-list workflow ([issue #211](https://github.com/cgbarlow/iris/issues/211)) *without* baking domain terminology into Iris core. The genericness was explicit user direction: "I don't want to create ANY functionality specific to ingredients, recipes, meals or whatever to Iris."

A discipline like this only holds with enforcement. ADR-182 established surface-parity as a CI-checked invariant; this ADR establishes a parallel **genericness invariant** with the same enforcement pattern.

## Decision

Add `scripts/check_aggregation_genericness.py` — a CI script that fails the build if any of a set of banned domain terms appears in `backend/app/` (excluding seed/migrations/tests/docs) or `frontend/src/` (excluding test fixtures and i18n strings).

### Banned strings (case-insensitive, word-boundary)

- `ingredient`, `ingredients`
- `recipe`, `recipes`
- `meal`, `meals`, `mealplan`
- `diners`
- `servings`
- `aisle`, `aisles`
- `grocery`, `groceries`
- `pantry`
- `shopping`

These are the words that, if they appear in Iris core code, would tell us a domain leak has happened. Per-domain values for these concepts (Quantity, Unit, Diners, Servings) live in seeded *data* (templates + profiles), never in code paths.

### Allow-listed paths

- `backend/app/migrations/` — migrations seed domain data; explicit purpose.
- `backend/app/seed/` — seed data, same.
- `backend/tests/` and `cli/tests/` and `mcp/tests/` — tests reference the seeded names.
- `docs/` — ADRs and specs deliberately use the words.
- `backend/app/import_sparx/` — unrelated EAP import code may legitimately mention "recipe" in a third-party context.
- `frontend/src/lib/i18n/` (if it ever exists) — translation strings.
- `**/CHANGELOG.md`, `**/README.md` — narrative.
- `*.md` files anywhere — docs are exempt.

### Enforcement

- Script exits non-zero on any banned match outside the allow-list.
- Wired into a new GitHub Actions workflow `.github/workflows/genericness-check.yml` that triggers on PRs touching `backend/app/aggregation/`, `backend/app/diagrams/`, `backend/app/element_templates/`, or `frontend/src/`.
- Standalone pytest invocation (`backend/tests/test_aggregation/test_genericness_invariant.py`) runs the script in-process so local test runs catch violations too.

### Versioning

This is a pure-process change: v6.21.1 (cleanup point release). No schema changes, no behaviour changes — just a guard against future regressions of the principle established in PRs 1–4.

## Consequences

**Positive:**

- A future PR that drops the word "ingredient" into a Python function or component name fails CI loudly.
- The genericness principle has the same enforcement weight as surface parity.
- The allow-list is small and meaningful — banned strings appear in seed data, docs, and tests; they should not appear in code.

**Negative / accepted trade-offs:**

- A genuinely unrelated use of one of these words gets caught. Mitigation: extend the allow-list with an ADR explaining why. The friction is intentional.
- Word-boundary matching may miss obfuscations (e.g. "groc"). The check is a tripwire, not a moat — humans review PRs too.

## Rejected alternatives

- **Code review only.** Easy to forget; not enforced; doesn't scale across contributors.
- **Pylint custom checker.** More machinery; pylint isn't otherwise in the build.
- **Tighter check (no domain terms in any file).** Breaks ADRs and tests; the point of the rule is that domain lives in *data*, not *code*.

## References

- [SPEC-214-a — banned list, allow-list, script implementation](./specs/SPEC-214-a-Genericness-Invariant.md)
- [`scripts/check_aggregation_genericness.py`](../../scripts/check_aggregation_genericness.py)
- [`.github/workflows/genericness-check.yml`](../../.github/workflows/genericness-check.yml)
- [ADR-182](./ADR-182-Surface-Parity-Discipline.md) — the parallel CI-enforced discipline.
