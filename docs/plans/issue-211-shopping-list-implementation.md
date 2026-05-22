# Implementation plan — Issue #211 meal-plan → shopping-list

**Status:** Draft, awaiting review (do not start implementation)
**Date:** 2026-05-22
**Branch:** `docs/issue-211-shopping-list-research` (this plan); implementation lands across multiple `feature/*` branches per protocol §4
**Companion research doc:** [`docs/analysis/issue-211-shopping-list-research.md`](../analysis/issue-211-shopping-list-research.md)

This plan implements the *Path C* design that emerged from the research discussion: four generic primitives that, in combination, deliver the shopping-list workflow without adding any domain-specific concept ("ingredient", "recipe", "meal", "aisle") to Iris core.

---

## 1. What we are building

### 1.1 Goal (functional)

Given a *meal plan* — a smart_markdown diagram listing the week's recipe diagrams with diner counts — produce a deduplicated, quantity-summed *shopping list* that the existing Claude Desktop + Chrome-extension grocery-shopping workflow can consume unchanged.

### 1.2 Acceptance criteria (from issue #211 and clarifying Qs)

- **AC1.** A user authoring a recipe in the smart_markdown editor can record an ingredient with a quantity in **one** `/`-picker interaction (via a stamp), without typing token syntax by hand.
- **AC2.** A user can mark a quantity slot as "to be filled in" (leave blank) and either edit it inline in the canvas or in the source pane.
- **AC3.** Given a meal plan diagram and the seeded "Shopping list" aggregation profile, a `GET` of the shopping-list diagram returns markdown grouped by aisle, with same-element quantities summed within matching units (500 g + 500 g pork mince = 1 kg).
- **AC4.** Servings scaling works: a recipe with `data.servings = 4` referenced in a meal plan with `diners = 6` contributes ingredient quantities at ×1.5.
- **AC5.** Mixed units on the same element across recipes (e.g., 500 g + 1 kg) emit two lines for that element — no cross-unit conversion (out of scope per Q3).
- **AC6.** The aggregation engine is callable directly over REST / MCP / CLI without any persisted aggregation-list diagram (Claude Desktop can call it directly during a session).
- **AC7.** Admin users can create, edit, and delete *global* aggregation profiles in admin settings. Set editors can do the same for *set-scoped* profiles inside the set editor.
- **AC8.** Nothing in the Iris core code base (excluding seed data and tests) contains the strings `"ingredient"`, `"recipe"`, `"meal"`, `"diners"`, `"servings"`, `"aisle"`, or `"shopping"` outside of comments, docs, and seed/migration files. The genericness invariant is testable.

### 1.3 Out of scope for v1 (explicit, per Q3)

- Cross-unit normalisation (g↔kg↔ml↔cups).
- Pantry deduction (subtracting on-hand items from the shopping list).
- Recurring meal-plan templates / calendar UX.
- Cost estimation.
- A general-purpose Iris function / DSL beyond aggregation (mentioned as a v2 direction).

### 1.4 The four generic primitives

| # | Primitive | Lives in | Generic invariant |
|---|---|---|---|
| **P1** | Token `=value` override on smart_markdown attribute references | `backend/app/diagrams/smart_markdown.py` (grammar + resolver); editor canvas (inline-editable spans) | Any token referencing a blank attribute renders as editable; `=value` syntax persists per-use values into markdown source |
| **P2** | `markdown_stamp` field on `element_templates`, with `{{self:…}}` placeholder | `backend/app/element_templates/` + smart_markdown picker | One-pick insertion of multi-token chunks against any element; stamp author UX is itself smart_markdown editing in self-mode |
| **P3** | `aggregation_profiles` library + generic aggregation engine | New module `backend/app/aggregation/` | Engine is a fixed kernel parameterised by profile JSON; same code path serves shopping-list, sprint-points, time-tracking, etc. |
| **P4** | `aggregation_list` synth-on-read diagram type | `backend/app/diagrams/aggregation_list.py` (thin wrapper) | Renders the engine output as markdown in the canvas; engine is callable independently |

Combined, these four primitives — none of which carry recipe semantics in their code paths — let the user build the shopping-list workflow from data alone (element schemas, stamps, profiles, source diagrams).

---

## 2. ADRs required

Per protocol §1, each architectural decision below gets its own ADR in `docs/adrs/`. Numbers are placeholders; assign at PR time from the next available number after the current highest (ADR-209 per recent commits → start at ADR-210).

| ADR | Title | Decides | Supersedes |
|---|---|---|---|
| **ADR-A** | Smart-markdown token `=value` overrides and blank-attribute editable spans | Grammar extension (`{{...:attr:path=value}}`); resolver precedence (override → stored → blank); canvas behaviour: blank tokens render as editable inputs that persist via in-place markdown source rewrite | Extends ADR-205, ADR-206 |
| **ADR-B** | Markdown stamps on element templates | New `markdown_stamp` column on `element_templates`; `{{self:…}}` self-reference token variant; substitution at insert time; picker integration (top section before fields); stamp authoring uses smart_markdown editor in self-mode | Extends ADR-191 (element templates) and ADR-205 |
| **ADR-C** | Generic aggregation profiles and aggregation engine | New `aggregation_profiles` table; profile_data JSON schema (traversal/output rules); engine module `backend/app/aggregation/`; surfaces (API/MCP/CLI); read-only, idempotent compute | Establishes new module |
| **ADR-D** | `aggregation_list` diagram type | Synth-on-read diagram type that delegates compute to the aggregation engine; configuration in `data.source_diagram_id` + `data.profile_id` | Extends ADR-186, ADR-187, ADR-205 |
| **ADR-E** | Genericness invariant for shopping-list workflow | Codifies that no code in `backend/app/` (excluding seed/migrations/tests/docs) may reference recipe-domain strings; CI check enforces this; rationale and exception list | Establishes new invariant; references ADR-182 (parity discipline pattern) |

Each ADR includes the rejected alternatives (Path A — element-graph recipes; Path B — domain-specific `ingredient`/`meal` token variants) and the rationale for rejecting them, per protocol §1.

---

## 3. Specs required

Per protocol §2, each implementation-bearing ADR gets a SPEC. Filenames follow `SPEC-{ADR-number}-{letter}-{Title}.md`.

| Spec | Pairs with | Scope |
|---|---|---|
| **SPEC-A-a-Smart-Markdown-Value-Overrides.md** | ADR-A | Grammar regex; resolver precedence; in-canvas inline-edit behaviour; persistence path; cursor / focus rules; edge cases (escaping `=`, multi-character values, special characters in values) |
| **SPEC-B-a-Element-Template-Stamps.md** | ADR-B | Schema; `{{self:…}}` substitution algorithm; picker UI integration; stamp-author editor UI in self-mode; in-scope-filter rules (template's captured element_type narrows applicability) |
| **SPEC-C-a-Aggregation-Profile-Schema.md** | ADR-C | Profile JSON schema (traversal, multiplier, output); SQLite + Supabase table; CRUD endpoints; scope rules (global vs set) |
| **SPEC-C-b-Aggregation-Engine.md** | ADR-C | Compute algorithm (pseudocode → Python); attribute-path resolution; multiplier resolution; aggregation function set (sum / mean / count); format string grammar; performance notes |
| **SPEC-C-c-Aggregation-Surfaces.md** | ADR-C | REST endpoints; MCP tools; CLI subcommands; surface parity; auth/RBAC; rate limiting (anonymous Ask-AI-style); audit-log entries on profile writes |
| **SPEC-D-a-Aggregation-List-Diagram-Type.md** | ADR-D | Diagram-type registration; data shape; synth-on-read hook; UI source/profile pickers in the create dialog |
| **SPEC-E-a-Genericness-Invariant.md** | ADR-E | List of banned strings; allow-listed paths (seed/, migrations/, tests/, docs/); `scripts/check_aggregation_genericness.py`; CI wiring |

---

## 4. Database changes (SQLite + Supabase migration pairs per §15)

All migrations land in pairs per protocol §15. SQLite uses `IF NOT EXISTS` + `INSERT OR IGNORE`; Supabase uses `IF NOT EXISTS` + `ON CONFLICT … DO NOTHING`; booleans in Supabase use `TRUE` / `FALSE`. Numbering picks up from the next free slot in each family at PR time.

### 4.1 Add `markdown_stamp` to `element_templates`

**SQLite** (`backend/app/migrations/m{N}_element_template_stamps.py`):

```sql
ALTER TABLE element_templates ADD COLUMN markdown_stamp TEXT;
```

**Supabase** (`backend/app/migrations/supabase/m{N}_element_template_stamps.sql`):

```sql
-- Mirrors SQLite m{N}.
ALTER TABLE element_templates ADD COLUMN IF NOT EXISTS markdown_stamp TEXT;
```

Schema test in `backend/tests/test_migrations/test_element_template_stamps_schema.py` — asserts column existence, idempotency on re-run, boolean-literal convention is not violated.

### 4.2 New `aggregation_profiles` table

**SQLite** (`m{N+1}_aggregation_profiles.py`):

```sql
CREATE TABLE IF NOT EXISTS aggregation_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    set_id TEXT REFERENCES sets(id),
    is_global INTEGER NOT NULL DEFAULT 0,
    profile_data TEXT NOT NULL,            -- JSON
    is_default_for_set INTEGER NOT NULL DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    CHECK ((is_global = 1 AND set_id IS NULL) OR (is_global = 0 AND set_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_agg_profiles_set ON aggregation_profiles(set_id) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_agg_profiles_global ON aggregation_profiles(is_global) WHERE is_deleted = 0;
```

**Supabase** (`m{N+1}_aggregation_profiles.sql`):

```sql
-- Mirrors SQLite m{N+1}.
CREATE TABLE IF NOT EXISTS aggregation_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    set_id TEXT REFERENCES sets(id),
    is_global BOOLEAN NOT NULL DEFAULT FALSE,
    profile_data JSONB NOT NULL,
    is_default_for_set BOOLEAN NOT NULL DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK ((is_global = TRUE AND set_id IS NULL) OR (is_global = FALSE AND set_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_agg_profiles_set ON aggregation_profiles(set_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_agg_profiles_global ON aggregation_profiles(is_global) WHERE is_deleted = FALSE;
```

Schema test mirrors the existing patterns (`test_response_format_prompts_schema.py`).

Note: `TIMESTAMPTZ` (Supabase) vs SQLite `TIMESTAMP` per the memory-of-prior-incident on the asyncpg datetime adapter.

### 4.3 Register `aggregation_list` diagram type

**SQLite** (`m{N+2}_aggregation_list_diagram_type.py`):

```python
INSERT OR IGNORE INTO diagram_types (id, name, description, notation, display_order, is_active)
VALUES (?, 'aggregation_list', 'Aggregation list', 'markdown', ?, 1);
```

**Supabase** (`m{N+2}_aggregation_list_diagram_type.sql`):

```sql
-- Mirrors SQLite m{N+2}.
INSERT INTO diagram_types (id, name, description, notation, display_order, is_active)
VALUES (?, 'aggregation_list', 'Aggregation list', 'markdown', ?, TRUE)
ON CONFLICT (id) DO NOTHING;
```

### 4.4 Seed global "Shopping list" aggregation profile

**SQLite + Supabase** (`m{N+3}_seed_shopping_list_profile.{py|sql}`):

Inserts one row into `aggregation_profiles` with `is_global = 1/TRUE`, `name = 'Shopping list'`, and the `profile_data` JSON from §5.3 of the research doc. Idempotent on re-run (skip if a row with the same `id` exists).

### 4.5 Optional: backfill `Quantity` attribute on existing grocery elements

Per Q5: yes, add `Quantity` attribute to grocery elements with blank value (treated as zero by the engine when blank). This is a **data migration**, not a schema migration — performed by a one-shot script `scripts/backfill_quantity_attribute.py` run by the operator against the target DB. The script:

1. Reads all elements in the `Groceries` set (set id is a CLI arg, not hard-coded).
2. For each element, checks if `data.attributes` already has an entry with `name == "Quantity"`; if not, appends `{"name": "Quantity", "type": "", "scope": "Public", "notes": "", "lower_bound": "", "upper_bound": ""}` and creates a new element version.
3. Dry-run mode prints the diff without writing.
4. Tests under `backend/tests/test_scripts/test_backfill_quantity_attribute.py` cover dry-run, idempotency, and the diff output.

This is **not** in the migration runner — it's an operator action because it's destination-specific (which set, which environment).

### 4.6 Migration of the 34 existing recipe diagrams

Script `scripts/migrate_recipes_to_quantity_tokens.py`:

1. Finds smart_markdown diagrams in a given set (set id is a CLI arg).
2. Regex-rewrites the existing `NNN {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}` pattern → `{{element:UUID:attr:attributes/Quantity/type=NNN}} {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}`.
3. Renders unchanged for the human reader (same string output).
4. Dry-run mode, idempotency, diff output, full revert script alongside.
5. Tests under `backend/tests/test_scripts/test_migrate_recipes_to_quantity_tokens.py` cover regex correctness, edge cases (no number prefix, decimal numbers, missing Unit attr), idempotency, and the revert path.

Also operator-run, not migration-runner.

### 4.7 Seed "Servings" attribute on recipe diagrams

For servings-scaling (AC4), each recipe diagram needs `data.servings: <int>`. Script `scripts/backfill_servings_on_recipes.py`:

1. For each smart_markdown diagram in a given set, prompts the operator interactively (or accepts a CSV mapping `diagram_id,servings`) and writes `data.servings` into the diagram's data blob.
2. Dry-run, idempotency, revert.

For the 34 existing recipes, the operator runs the CSV path with values the user supplies offline. The plan documents this in the release notes.

---

## 5. Backend modules

### 5.1 New module: `backend/app/aggregation/`

Per protocol §13 (DRY) — the engine has one home.

```
backend/app/aggregation/
  __init__.py
  models.py                  # AggregationProfile (pydantic), AggregationRequest, AggregationResult
  schema.py                  # JSONSchema for profile_data validation
  profiles_service.py        # CRUD for aggregation_profiles
  engine.py                  # the generic kernel
  attribute_resolver.py      # resolve_attribute(token, path) — reads override or stored value
  multiplier_resolver.py     # resolve_multiplier(token, ref_diag_id, rule)
  format_renderer.py         # apply line_format / breakdown_format / group_by
  routes.py                  # FastAPI router mounted at /api/aggregation
  exceptions.py
  tests/
    test_engine.py
    test_attribute_resolver.py
    test_multiplier_resolver.py
    test_format_renderer.py
    test_profile_crud.py
    test_routes.py
```

### 5.2 Smart-markdown extensions in `backend/app/diagrams/smart_markdown.py`

- Update `_TOKEN_RE` to capture optional `=value` tail on attribute references.
- Add `_resolve_one` branch: if token carries `=value` override, return that; else fall through to the existing element-attr lookup.
- Add `{{self:…}}` recognition path that *errors loudly* if encountered in a normal recipe context (self-tokens only valid inside stamp definitions; the resolver substitutes them before insertion, so they should never reach the runtime resolver).
- Tests in `backend/tests/test_diagrams/test_smart_markdown.py` extended to cover overrides, blank handling, escape semantics.

### 5.3 Element-template extensions in `backend/app/element_templates/`

- New field on `ElementTemplateCreate` / `ElementTemplateResponse` pydantic models: `markdown_stamp: str | None`.
- `service.py` updated to read/write the column.
- A new service function `substitute_self(stamp_body: str, element_id: str) -> str` — replaces `{{self:<field-spec>}}` with `{{element:<id>:<field-spec>}}`. Used by the picker at insert time.
- A new endpoint helper for the picker to fetch in-scope stamps for a given element context.

### 5.4 New diagram type wrapper in `backend/app/diagrams/aggregation_list.py`

- Synth-on-read function `compute_aggregation_list_content(diagram, db) -> str` (mirrors `dynamic_list.py` / `smart_markdown.py` shape).
- Reads `data.source_diagram_id` + `data.profile_id`.
- Calls `aggregation.engine.run(profile_id=..., source_diagram_id=..., db=db)` and returns the markdown.
- Service dispatch hook in `backend/app/diagrams/service.py::_maybe_synthesise_content` extended to dispatch on `diagram_type == "aggregation_list"`.

### 5.5 Genericness CI check

`scripts/check_aggregation_genericness.py`:

- Walks `backend/app/` excluding `seed/`, `migrations/`, `tests/`, and any path matching the spec's allow-list.
- Greps for the banned strings (`ingredient`, `recipe`, `meal`, `diners`, `servings`, `aisle`, `shopping`, case-insensitive).
- Exits non-zero on any match.
- Wired into CI on every PR touching `backend/app/aggregation/`, `backend/app/diagrams/`, or `backend/app/element_templates/`.

The check mirrors `scripts/check_surface_parity.py` (ADR-182) in style.

---

## 6. API surfaces

All routes follow the existing `/api/<resource>/<action>` conventions and use the same auth/RBAC middleware.

### 6.1 Aggregation profile CRUD (writes — need surface parity per §14)

| Method + Path | Purpose |
|---|---|
| `GET /api/aggregation/profiles` | List in-scope profiles (filter by `set_id`, `is_global`) |
| `GET /api/aggregation/profiles/{id}` | Fetch one profile |
| `POST /api/aggregation/profiles` | Create — admin (global) or set-editor (set-scoped) |
| `PATCH /api/aggregation/profiles/{id}` | Update |
| `DELETE /api/aggregation/profiles/{id}` | Soft-delete |
| `POST /api/aggregation/profiles/{id}/restore` | Restore from recycle bin (matches existing patterns) |

### 6.2 Aggregation run (read-shaped, idempotent)

| Method + Path | Purpose |
|---|---|
| `POST /api/aggregation/run` body `{profile_id?, inline_profile?, source_diagram_id}` | Compute and return `{markdown, computed_at, source_versions}` |

Read-shaped despite being POST (because the body carries the profile reference + source). Not subject to write parity, but does need MCP + CLI parity for usability.

### 6.3 Stamp helper (read)

| Method + Path | Purpose |
|---|---|
| `GET /api/element-templates/stamps?element_id={id}` | Returns in-scope stamps for the given element (filtered by set, element_type) |

Read endpoint; powers the picker. Implementation lives in `backend/app/element_templates/service.py`.

### 6.4 Surface parity check

`scripts/check_surface_parity.py` (existing per ADR-182) needs an update to its exception list **only if** any of the above writes legitimately lack an MCP or CLI counterpart. Default: every write has both. Surface-parity table updates:

- `POST /api/aggregation/profiles` → MCP `create_aggregation_profile`, CLI `iris aggregation-profile create`
- `PATCH /api/aggregation/profiles/{id}` → MCP `update_aggregation_profile`, CLI `iris aggregation-profile update`
- `DELETE /api/aggregation/profiles/{id}` → MCP `delete_aggregation_profile`, CLI `iris aggregation-profile delete`
- `POST /api/aggregation/profiles/{id}/restore` → MCP `restore_aggregation_profile`, CLI `iris aggregation-profile restore`

Plus for the `markdown_stamp` field on element templates — handled by existing element-template write surfaces (since stamp is just a field on an existing entity, the existing `create_element_template` / `update_element_template` MCP/CLI surfaces gain it for free via pydantic-model expansion).

---

## 7. MCP tools

Per protocol §14, each backend write gets a matching MCP tool. Per the analysis doc and the "make it an Iris function" framing, the `aggregate` tool is the linchpin.

| Tool | Purpose | Read/Write |
|---|---|---|
| `aggregate` | Run a profile against a source diagram; returns markdown | Read |
| `list_aggregation_profiles` | List in-scope profiles | Read |
| `get_aggregation_profile` | Fetch one profile | Read |
| `create_aggregation_profile` | Create | Write |
| `update_aggregation_profile` | Update | Write |
| `delete_aggregation_profile` | Soft-delete | Write |
| `restore_aggregation_profile` | Restore | Write |
| `list_element_template_stamps` | List in-scope stamps for an element | Read |

The `aggregate` tool is what Claude Desktop calls during a session. Its tool description is written for agent discoverability: "Run a named aggregation profile against a source diagram. Returns aggregated markdown. Use this when you need a deduplicated, summed roll-up across multiple linked diagrams (e.g., to build a shopping list from a meal plan)."

---

## 8. CLI

Per protocol §14, parity with MCP/REST. CLI subcommand structure:

```
iris aggregation-profile create   --name <s> [--set <id>] [--global] [--profile-data-file <path>]
iris aggregation-profile update   --id <id> [--name <s>] [--profile-data-file <path>]
iris aggregation-profile list     [--set <id>] [--global]
iris aggregation-profile get      --id <id>
iris aggregation-profile delete   --id <id>
iris aggregation-profile restore  --id <id>

iris aggregate                    --profile <id-or-name> --source <diagram-id-or-name>
                                  [--inline-profile-file <path>]
```

Existing `iris element-template create`/`update` accept a new `--markdown-stamp` flag.

---

## 9. Frontend changes

### 9.1 Smart-markdown canvas (per ADR-A)

- `SmartMarkdownCanvas.svelte` — tokens whose value override is blank (`…/type=`) render as an inline `<input>` element. On blur, the canvas rewrites the token in the markdown source from `…/type=` → `…/type=<value>` and re-runs the resolver. Per protocol §7, no `{@html}` paths change here — values are rendered as text content of input elements; markdown rendering still goes through the existing marked + DOMPurify pipeline.
- New picker option "Insert as fillable placeholder" surfaces in the field-step.
- Source-pane editing of `=value` is supported as a fallback.

### 9.2 Smart-markdown picker — stamp section (per ADR-B)

- After entity selection, the picker shows a "Stamps" section above the "Fields" section.
- Stamps are fetched via `GET /api/element-templates/stamps?element_id=...`.
- Picking a stamp inserts the resolved stamp body (with `{{self:…}}` substituted server-side or client-side; client-side is simpler).
- Stamps with `template_data.element_type` matching the selected element appear; non-matching are hidden (per Q1 resolution).
- A "Manage stamps" link in the picker footer navigates to the element-template editor for users with rights.

### 9.3 Element-template editor — stamp editor (per ADR-B)

- New "Stamp" tab in the element-template editor.
- Editor uses the same smart_markdown component but with a `selfMode: true` prop:
  - Picker skips entity step; defaults to `{{self:…}}` tokens.
  - Live preview renders the stamp against the template's `source_element_id`.
  - Preview prompts for test values for any blank slots so the user sees a realistic render.

### 9.4 Aggregation-profile editor (per ADR-C)

A new component `AggregationProfileEditor.svelte` reused in two contexts:

- **Admin settings → new "Aggregation profiles" tab** — lists `is_global = true` rows; create / edit / delete.
- **Set editor → new "Aggregation profiles for this set" section** — lists set-scoped rows; same editor.

The editor renders the profile JSON as a form:

- **General** tab: name, description, scope (locked).
- **Traversal** tab: outer (collapsible) + inner steps. Each step: collect-token-type dropdown; attribute-path picker (reusing the smart_markdown attribute-path picker as a sub-component); skip-blank-values toggle.
- **Multiplier** tab (only when outer step is enabled): numerator-from-override attribute-path picker; divisor-from-diagram-data dotted-path input with validation; default-multiplier number.
- **Output** tab: group-by attribute-path picker; sort-groups + sort-items-within-group dropdowns (`alpha`, `package_display_order`, `none`); line-format + breakdown-format text inputs with placeholder autocomplete (`{name}`, `{sum_value}`, `{bucket}`, `{sources_joined}`).
- **Preview** tab: source-diagram picker → live-rendered output of the engine against the current in-memory profile draft.

### 9.5 Aggregation-list diagram (per ADR-D)

- New create-diagram option "Aggregation list" in the diagram type dropdown.
- Create dialog includes: source diagram picker (any diagram), profile dropdown (in-scope profiles).
- Read view: standard markdown render of the synthesised content (same component as smart_markdown / dynamic_list).
- Edit view: source/profile pickers in a Source panel (matching the `dynamic_source` UX from ADR-186 dynamic-list).

### 9.6 Frontend dependencies

Per protocol §11 — check latest stable versions of any new dependencies at PR time. No new dependencies are anticipated; everything reuses existing Svelte / TailwindCSS / xyflow stack.

---

## 10. Tests strategy (per protocol §3 — TDD)

Red-green-refactor across every layer. Tests written before implementation; coverage cannot decrease.

### 10.1 Backend test layout

```
backend/tests/
  test_aggregation/
    test_engine.py                   # walk, group, sum, format — generic only
    test_attribute_resolver.py
    test_multiplier_resolver.py
    test_format_renderer.py
    test_profile_crud.py
    test_routes.py
    test_aggregate_run_endpoint.py
    test_aggregate_via_mcp.py        # end-to-end through MCP tool
    test_genericness_invariant.py    # runs the genericness CI script
  test_diagrams/
    test_smart_markdown.py           # extended for =value overrides
    test_aggregation_list.py         # new
  test_element_templates/
    test_stamps.py                   # markdown_stamp CRUD + self-substitution + scope filter
  test_migrations/
    test_element_template_stamps_schema.py
    test_aggregation_profiles_schema.py
    test_aggregation_list_diagram_type_schema.py
    test_seed_shopping_list_profile_schema.py
  test_scripts/
    test_backfill_quantity_attribute.py
    test_migrate_recipes_to_quantity_tokens.py
    test_backfill_servings_on_recipes.py
```

### 10.2 Frontend test layout

- Vitest unit tests for `SmartMarkdownCanvas.svelte` inline-edit behaviour (cursor positions, persistence to source, escape handling).
- Component tests for the new picker stamp section and the stamp editor.
- Component tests for `AggregationProfileEditor.svelte` covering each tab and the preview.
- Component tests for the aggregation-list create dialog and read view.
- Playwright e2e: author a recipe via stamp; build a meal plan; view the seeded shopping-list aggregation diagram; verify the markdown reflects the expected aggregation.

### 10.3 Genericness invariant test (per ADR-E)

A single pytest invokes `scripts/check_aggregation_genericness.py` and asserts exit code 0 across the entire current tree. Failures point at the offending file + line.

---

## 11. Documentation updates (per protocols §1, §2, §5, §12)

- All ADRs (§2 of this plan) — created.
- All specs (§3 of this plan) — created.
- `CHANGELOG.md` — entries under `[Unreleased]` for each shipped PR; moved under the version heading at release.
- `README.md` — update the Features table:
  - "Smart Markdown" row: note `=value` overrides and stamps.
  - New row for "Aggregation List" diagram type.
- `docs/api.md` — new endpoints under `/api/aggregation/`.
- `docs/cli.md` — new `iris aggregation-profile` and `iris aggregate` subcommands.
- `docs/mcp.md` — new MCP tools listed.
- `docs/north-star.md` — refresh the "Iris as a prototyping tool" framing with shopping list as the worked example.

---

## 12. Versioning and release plan (per §5, §6)

SemVer per protocol §6. Current version: `v6.12.0` (from CHANGELOG).

Recommended cadence — one minor version per primitive shipped end-to-end:

| Version | Ship |
|---|---|
| `v6.13.0` | ADR-A: smart-markdown `=value` overrides + blank-attribute inline edit |
| `v6.14.0` | ADR-B: element template stamps (schema + picker + stamp editor) |
| `v6.15.0` | ADR-C: aggregation profiles + engine + REST/MCP/CLI surfaces; seed shopping-list profile |
| `v6.16.0` | ADR-D: `aggregation_list` diagram type; admin + set-editor UI for profiles |
| `v6.16.1` | ADR-E: genericness invariant CI check (cleanup PR after the above) |
| `v6.17.0` | Operator-run data migrations (Quantity attribute, recipe rewrites, servings backfill) + end-to-end demo verification |

Each release: tag, GitHub Release per memory (`feedback_release_workflow`), CHANGELOG roll, four-place version bump per memory (`feedback_iris_version_bump_discipline`) — frontend/package.json + backend/mcp/iris-client pyproject.toml.

Per memory `feedback_render_supabase_ordering`: for the versions with Supabase migrations (v6.13–v6.17), the release sequence is migration-only PR → `scripts/supabase-migrate.sh` against UAT → code-change PR. CHANGELOG entries call this out per release.

---

## 13. PR / branch breakdown (per protocol §4)

One logical change per branch. Suggested order:

1. **`feature/smart-markdown-value-overrides`** — ADR-A + SPEC-A-a + grammar/resolver + canvas inline edit + tests + CHANGELOG → v6.13.0.
2. **`feature/element-template-stamps`** — ADR-B + SPEC-B-a + schema migration + service + picker + stamp editor + tests + CHANGELOG → v6.14.0.
3. **`feature/aggregation-profiles-and-engine`** — ADR-C + 3 specs + migrations + module + routes + MCP + CLI + tests + CHANGELOG → v6.15.0.
4. **`feature/aggregation-list-diagram-type`** — ADR-D + SPEC-D-a + migration + diagram wrapper + frontend create dialog + read/edit canvas + tests + CHANGELOG → v6.16.0.
5. **`feature/aggregation-genericness-invariant`** — ADR-E + SPEC-E-a + CI script + tests + CHANGELOG → v6.16.1.
6. **`feature/shopping-list-demo-migration`** — operator-run scripts (backfill Quantity, rewrite recipes, backfill servings) + tests + release notes + CHANGELOG → v6.17.0.

Each PR closes one ADR's worth of work, has tests, has a CHANGELOG entry, and gets a GitHub Release.

Parallelisable per protocol §10: PRs 1 and 2 are independent (different modules) and could ship in either order or in parallel via worktrees. PR 3 depends on neither but doesn't deliver user value until paired with PR 4. PR 5 and 6 are independent of each other and depend on PRs 1-4 being in.

---

## 14. Open items (need user confirmation before implementation)

These were flagged in the research doc and clarifying-questions exchange but not yet definitively answered. Putting them here so they don't get lost.

| # | Item | My recommendation | Awaiting user input |
|---|---|---|---|
| O1 | Should `inline_profile` (one-off, not saved) be supported in `POST /api/aggregation/run`, or only `profile_id`? | Only `profile_id` in v1; inline as v1.1 if asked for. | Confirm |
| O2 | Default `aggregation_fn` set: `sum` only, or `sum + mean + count + max + min`? | `sum + count` in v1 (mean/max/min in v2 — small additions). | Confirm |
| O3 | Where does "Servings" live on a recipe? `diagram.data.servings` (free-JSON, no schema change) **or** a structured attribute on a Recipe element? Q4 said meal plan = smart_markdown listing recipes via diagram tokens, so the recipe-as-diagram path is locked. But the `servings` value still needs a home. Recommend `diagram.data.servings: <int>`. | `diagram.data.servings: <int>`. Profile reads it via `multiplier.divisor_from_diagram_data = "data.servings"`. | Confirm |
| O4 | Should `markdown_stamp` field accept multiple stamps per template (JSON array of `{name, body}`) or one per template (and you add multiple templates)? | One per template — keeps `element_templates` semantics clean. Multiple stamps = multiple templates with different names. | Confirm |
| O5 | Anonymous access: should `POST /api/aggregation/run` be callable anonymously (like Ask AI's stricter rate limit) or auth-only? | Auth-only in v1 — the engine touches the diagrams it walks; anon already has read access to those diagrams; reconsider in v1.1 if needed. | Confirm |
| O6 | Genericness invariant — banned-string list final cut: `ingredient`, `recipe`, `meal`, `diners`, `servings`, `aisle`, `shopping`. Anything to add/remove? | List as proposed; add `groceries` and `pantry`? Borderline since "Pantry" is a package name in user data, not in code. Probably leave both off. | Confirm |
| O7 | Genericness invariant — should the check also extend to the **frontend** (`frontend/src/`)? | Yes — same rules, same allow-list (i18n strings, test fixtures, seed data only). | Confirm |
| O8 | Naming: profile referred to as "aggregation profile" throughout. Any preference for "rollup profile", "aggregator profile", or other? | Keep "aggregation profile" — matches the `aggregation_list` diagram type, the `/api/aggregation/` route prefix, and the `aggregate` MCP tool. | Confirm |
| O9 | Should the seeded "Shopping list" profile ship in v6.15.0 (with the engine) or in v6.16.0 (with the aggregation_list UI)? | v6.15.0 — useful from MCP/CLI even before the diagram-type UI lands. | Confirm |

---

## 15. Surface parity check — ADR-182 expectations

Per protocol §14 and the existing parity script: every new write endpoint listed in §6 of this plan ships with its MCP tool and CLI subcommand in the same PR. The parity script's exception list does *not* need new entries — the new endpoints follow the standard pattern.

The aggregation-list diagram type is *not* a new write surface; it rides on the existing diagram CRUD. No parity changes needed for it beyond the diagram-type registration in the seed.

---

## 16. SQLite ↔ Supabase parity — ADR-182 expectations (per §15)

All four migrations (§4) ship in pairs. Specifics that need extra care, given the memory of prior incidents:

- `aggregation_profiles.is_global` and `.is_default_for_set` and `.is_deleted` — **`BOOLEAN` in Supabase with `TRUE`/`FALSE` literals**, `INTEGER` in SQLite with `0`/`1`. Schema test enforces.
- `aggregation_profiles.created_at` / `updated_at` — **`TIMESTAMPTZ` in Supabase**, `TIMESTAMP` in SQLite. Per memory: asyncpg converts ISO strings to datetime; TEXT columns reject the bind. Schema test enforces.
- `aggregation_profiles.profile_data` — `TEXT` in SQLite, `JSONB` in Supabase. Both stored/read as JSON strings at the service layer (per the existing pattern for `element_templates.template_data`). Service-layer reads via positional indexing (`r[N]`), never `row["col"]`, per memory.
- No dollar-quoted SQL / triggers / functions in any of the SQL files — keeps `scripts/supabase-migrate.sh` simple.

---

## 17. Latest stable dependencies — protocol §11 expectations

No new dependencies are anticipated. Re-verify before each PR:

- Backend stays on existing FastAPI / aiosqlite / asyncpg / pydantic versions.
- Frontend stays on existing SvelteKit 5 / @xyflow/svelte / Tailwind 4 / marked / DOMPurify versions.
- If a new dependency is unavoidable (unlikely — perhaps a JSONSchema validator for profile_data?), check PyPI / npm registry for the latest stable, pin, document the date in the commit message.

---

## 18. Security — protocol §7

The aggregation engine produces markdown that flows through the existing markdown → marked → DOMPurify pipeline. **No new `{@html}` paths are introduced.** The inline-editable spans for blank attributes are real `<input>` elements with text-content values, not innerHTML — they don't bypass Svelte's escaping.

Profile JSON is validated against the JSONSchema in `aggregation/schema.py` before persistence — protects against malformed profiles, oversized payloads, recursive references, etc.

`POST /api/aggregation/run` rate-limited via existing middleware (per the anon Ask-AI patterns) once O5 is decided.

---

## 19. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Profile JSON gets gnarly for users editing it; the form UX in §9.4 is on the path | Build the form-style editor first (not a raw-JSON editor). Add a "View raw JSON" toggle for advanced users. Validate aggressively on submit; surface errors inline. |
| The genericness invariant (ADR-E) blocks legitimate doc/seed/comment uses | The allow-list is path-based + comment-aware; if false positives surface, broaden the allow-list rather than the banned list. |
| Existing recipes (the 34) get out of sync between rewrite migration and the v6.15 release | Operator-run scripts ship in v6.17.0 *after* the engine and diagram type are stable; before that, recipes still render fine — they just aren't on any aggregation. Migration is reversible. |
| Servings is missing on most existing recipes | Scaling default = 1 when servings missing or 0 (i.e., no scaling, pass through). A warning marker can render in the aggregated output. Operator backfills in v6.17 with user-supplied values. |
| Performance: aggregating 30+ recipes on every GET | Profile data is small; recipe markdown is small; engine is O(tokens) and runs synchronously. If problematic at scale, add a per-diagram cache invalidated on source-diagram version bump (standard pattern). Not a v1 concern. |
| Surface parity script fails on the new endpoints | Run locally before pushing each PR (`python scripts/check_surface_parity.py`). |
| Supabase migration runs out of pipeline minutes per memory | Plan release windows; if a near-instant build_failed appears, check Render `/events` for `pipeline_minutes_exhausted` per memory `feedback_render_pipeline_minutes` before debugging code. |

---

## 20. Demo verification (issue #211 end-to-end)

When v6.17.0 ships, the issue-211 acceptance test is:

1. User takes a photo of the kitchen jotter pad.
2. Claude (Desktop) is asked to "build this week's meal plan and shopping list from this photo."
3. Claude:
   - Uses Ask-AI / vision to read the jotter.
   - Calls `iris search` (existing) to resolve recipe names → diagram IDs.
   - Calls `create_diagram` (existing) to create a new smart_markdown meal-plan diagram with `{{diagram:<id>:attr:attributes/Diners/type=<N>}}` tokens for each meal (the `Diners` attribute is what the seeded shopping-list profile reads via `multiplier.from_attribute_override`).
   - Calls `aggregate(profile="shopping-list-global", source_diagram_id=<new-meal-plan>)` → returns the markdown shopping list.
4. Claude posts the shopping list back to the user.
5. User reviews; if happy, hands off to the Chrome extension which uses the same markdown to drive the Woolworths order.

If steps 3 and 4 work end-to-end without any custom code beyond what this plan delivers, we're done.

---

## 21. Out-of-band items I'm not touching in this plan

- The merge-conflicted `frontend/src/lib/components/KnowledgeGraph.svelte` and the staged `frontend/vite.config.ts` modification on the local `main` branch — separate work, separate PR, not this initiative.
- The other in-flight untracked plans/prompts in `docs/plans/` and `docs/prompts/` (e.g., `fizzing-tardle-whomp.md`, `doview-book-prompt-a.md`) — unrelated.
- The Issue #185 follow-ups for smart_markdown (worktree at `.claude/worktrees/smart-markdown-and-tab-defaults/`) — this plan extends smart_markdown but assumes ADR-205 / ADR-206 / ADR-209 are merged before v6.13.0 begins. If they aren't, the plan's PR sequence merges them first.

---

## 22. Summary in one paragraph

Four generic primitives — token `=value` overrides, element-template markdown stamps, an aggregation-profile library plus a generic aggregation engine exposed as a first-class Iris function over REST/MCP/CLI, and an `aggregation_list` synth-on-read diagram type — combine to deliver issue #211's shopping-list workflow without adding any recipe-specific concept to Iris core. The shopping-list flavour lives entirely in user-managed data: a `Quantity` attribute on grocery elements, a "Quantified item" stamp on a grocery-item element template, and a seeded global "Shopping list" aggregation profile. The four primitives ship across five minor releases (v6.13 → v6.17) plus one cleanup point release, each on its own feature branch, with paired SQLite + Supabase migrations, ADRs, specs, surface-parity-compliant MCP and CLI tooling, TDD-driven test coverage, and a CI-enforced genericness invariant that bans recipe-domain strings from Iris code. The capability is reusable — the same engine produces sprint-points rollups, time logs, expense reports, and anything else fitting the walk-tokens-collect-attributes-group-sum-format pattern — and the entire shopping-list workflow can be exercised directly from Claude Desktop via the `aggregate` MCP tool without any UI ever being opened.
