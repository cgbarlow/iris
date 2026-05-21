# Issue #211 — Meal plan → shopping list: research & design analysis

**Status:** Research report, awaiting decision
**Date:** 2026-05-21
**Author:** Claude (research session)
**Scope:** Design the missing piece of the Iris-powered autonomous-grocery-shopping demonstration: turn a weekly meal plan into a deduplicated, quantity-summed shopping list.

---

## 1. Problem framing

The autonomous-grocery proof-of-concept works end-to-end *when the shopping list already exists*. The hand-off is:

```
Iris (shopping list) --MCP--> Claude Desktop --Chrome ext--> Woolworths
```

What's missing in front of that hand-off is the **synthesis step**: take the week's meal plan (a chosen set of recipes plus how many diners each will feed) and produce a single aggregated shopping list — one line per grocery item, quantities summed across recipes, in a form the agent can shop.

Two explicit functional requirements from the brief:

- **R1. Cross-recipe aggregation.** `500 g pork mince` in Bolognese + `500 g pork mince` in Cottage Pie → `1 kg pork mince` (one line) on the list.
- **R2. Servings scaling** (user-confirmed in clarifying Q3). Recipe declares it serves N; meal plan declares M diners for that meal; quantities scale `M/N`.

Two requirements explicitly *out of scope* (user-rejected in Q3):

- **Unit normalisation across families** (g↔kg↔ml↔cups). Out of scope for v1; same-unit sum only.
- **Pantry deduction** (subtracting items already at home). Out of scope for v1.

And one architectural requirement from the brief:

- **R3. "Natural" and "not brittle."** The feature must compose with Iris's existing model rather than bolting on a new parallel system, and the data layout must be machine-parseable rather than relying on fragile string extraction.

---

## 2. What's already in the model (UAT inspection)

The `Day to day living` collection on `iris-uat.chrisbarlow.nz` (id `705058c2-…`) has **two sets**:

### 2.1 `Groceries` set (id `12866e48-…`)

- **178 elements**, **13 root packages** functioning as **aisles**: Bakery, Beverages, Canned Goods, Cereals & Breakfast, Chilled, Deli, Frozen, Gluten-free, Household, Meat & Poultry, Pantry, Personal Care, Produce.
- Each element is `element_type = "class"` (UML notation reused) with a structured `data.attributes[]` array. Example — Pork mince (`a8db6014-…`):

  ```json
  {
    "attributes": [
      {"name": "Unit", "type": "g", "scope": "Public", ...},
      {"name": "Products", "type": "WW Free Farmed NZ Pork Rump Steak", ...},
      {"name": "Products", "type": "WW Free Farmed Pork Fillet Whole", ...},
      {"name": "Preferred product", "type": "WW Free Farmed NZ Pork Rump Steak", ...}
    ]
  }
  ```

- **Semantics already encoded per grocery item:** a default unit (`Unit/type`), one or more candidate Woolworths SKUs (`Products[*]/type`), and a preferred SKU (`Preferred product/type`). This is the contract the Chrome extension uses to shop.

### 2.2 `Meal plans` set (id `ef57c7e7-…`)

- **0 elements, 34 diagrams.** Recipes are not elements with relationships — they are diagrams of type `smart_markdown` (`notation = markdown`).
- Each recipe is a markdown document whose body contains **`smart_markdown` tokens** that resolve at GET time against live element data. Example — `Burgers` `markdown_source`:

  ```markdown
  - {{element:3a4ccf73-…:name}}
  - {{element:41914a59-…:name}}
  - {{element:7c6c5f73-…:name}}
  - {{element:031e9f0a-…:name}}
  - 500 {{element:a8db6014-…:attr:attributes/Unit/type}} {{element:a8db6014-…:name}}
  - {{element:bc4df447-…:name}}
  ```

  This renders as (note line 5):

  ```
  - Eggs
  - Buns
  - Tomato
  - Lettuce
  - 500 g Pork mince
  - Onion
  ```

- The token grammar (ADR-205 / ADR-206, v6.14–v6.15): `{{<entity-type>:<id>:<field-spec>}}` where `field-spec` is `name | description | attr:<path>`. Unresolvable tokens render as `~~{{…}}~~`. Implemented in `backend/app/diagrams/smart_markdown.py` (in the smart-markdown worktree; not yet merged to `main` as of this report).

### 2.3 No Meal Plan exists yet

There are 34 recipe diagrams but **no diagram or package representing "this week's meals"** — no record connecting "Bolognese on Monday, Cottage Pie on Tuesday" to a single aggregable unit. The "meal plan" concept is presently in the user's head (or on the kitchen jotter pad).

---

## 3. Iris capabilities relevant to the feature

| Capability | What it gives us | Source |
|---|---|---|
| `element.data` JSON blob | Unbounded structured attributes per element | `backend/app/elements/models.py:27` |
| `relationship.data` JSON blob + `label` | Unbounded attributes on edges (qty/unit could live here) | `backend/app/relationships/models.py:8–24` |
| Free-form `element_type` strings | "recipe", "ingredient", "meal_plan" need no registration | `backend/app/elements/models.py:24` |
| **`smart_markdown` diagram type** | Already used for all 34 recipes; templating resolves entity field references at read time | `backend/app/diagrams/smart_markdown.py` (worktree) |
| **`dynamic_list` diagram type** (v6.7.0, ADR-186) | Synthesises a bullet list from diagram relationships **or** package elements at read time | `backend/app/diagrams/dynamic_list.py` |
| Synth-on-read hook (ADR-187) | Standard pattern for "computed content" diagram types; output lands in `data.content`, consumed unchanged by md/docx/pdf renderers | `backend/app/diagrams/service.py::_maybe_synthesise_content` |
| Batch element create/update (v6.10.0, ADR-200) | Bulk-load ingredients in one MCP call; ADR-200 explicitly names "grocery-list-sized batches" as the motivating case | `backend/app/batch/` |
| Artefact store (v6.2.0, ADR-179) | Persist generated markdown as `.md` / `.docx` / `.pdf` with a downloadable URL | `backend/app/artefacts/` |
| MCP / CLI / API surface parity (v6.6.0, ADR-182) | Whatever endpoint we add gets a matching MCP tool and CLI subcommand for free (and is enforced in CI) | `scripts/check_surface_parity.py` |
| Response-format prompts (v5.12.0, ADR-157) | Layered AI prompt cascade — could enforce "Shopping list" output shape if AI is in the synthesis path | `backend/app/ai/models.py:164–271` |

**Key observation:** Iris already has a synth-on-read diagram pattern (`dynamic_list`, `smart_markdown`) that computes structured content from live data at GET time. A shopping list is precisely that — a derived view that should always reflect the current meal plan + current grocery item attributes. **A new synth-on-read diagram type is the natural surface.**

---

## 4. The structured-quantity problem

The user's Q1 selection — "store quantity/unit as relationship attribute on a `Recipe -[contains]-> Ingredient` edge" — is the right model in the abstract. But it doesn't match the current state: there are no Recipe *elements*, only Recipe *diagrams*, and there are no `contains` relationships, only inline `smart_markdown` tokens with **plain-text quantity prefixes** like `500 {{element:…:attr:attributes/Unit/type}} {{element:…:name}}`.

This is the central design tension. Two coherent paths forward:

### Path A — Migrate recipes to structured elements

Convert each recipe diagram into:

1. A `Recipe` element (carrying `data.servings: 4`).
2. One `relationship_type = "contains"` per ingredient, with `data: {qty: 500, unit: "g"}` on the edge.

A future "ingredients of this recipe" view (a dynamic_list rendering Recipe → contains → Ingredient edges) replaces the smart_markdown body.

**Pros**: machine-parseable everywhere; relationships visible in the Knowledge Graph; existing batch tooling fits; cleanest aggregation logic.

**Cons**: forces a migration of all 34 recipes; loses the free-form markdown body (cooking *method*, notes, photos — anywhere the user writes prose between ingredients); recipes become brittle to model in cases like "a pinch of salt" or "to taste" where there is no numeric quantity.

### Path B — Extend `smart_markdown` with a structured quantity token (recommended)

Add a single new token grammar variant the resolver understands:

```
{{ingredient:<element-id>:qty:<number>[:unit:<unit-override>]}}
```

Resolves (at read time) to the same `"500 g Pork mince"` string the user already writes, by looking up the element's name and (if `unit:` is omitted) its `attributes/Unit/type`. **And** the same token is machine-extractable: the existing `_TOKEN_RE` regex already isolates `entity-type:id:field-spec`; adding `ingredient` as a fifth entity-type variant means the aggregator can scan a recipe's `markdown_source`, pull every `ingredient` token, and read qty+unit+element-id directly.

The free-text prose stays free text. The 34 existing recipes need a one-shot rewrite of their numeric-quantity lines (an MCP-driven migration: regex out the existing `NNN {{element:UUID:attr:…/Unit/…}} {{element:UUID:name}}` pattern and rewrite as `{{ingredient:UUID:qty:NNN}}`). A "pinch of salt" line stays as it is — `{{element:UUID:name}}` with prose around it — and is simply ignored by the aggregator.

**Pros**: zero loss of the recipe-as-document UX; aggregator never has to parse natural-language quantities; recipes still validate visually because rendered output is identical; composes with everything else in the system (Knowledge Graph, search, response-format prompts).

**Cons**: a new token variant is an addition to ADR-205's grammar (would need ADR-205.x or a new ADR superseding); needs a tiny migration of the 34 recipes.

### The user's Q1 answer reconciled

The Q1 preview the user chose said *"leverages existing extensible relationship JSON blob, no new element types needed."* The spirit of the answer is **"put quantities in a structured machine-readable place."** Path B honours that intent without forcing the path A migration of all 34 recipe diagrams into element-graph form. **Recommendation: Path B**, with Path A noted as the long-run direction if recipes ever need to be first-class entities (e.g., for "find every recipe that uses pork mince" queries the KG could answer directly).

---

## 5. Meal-plan modelling

A meal plan needs to record: (a) which recipes are in scope, (b) how many diners each meal feeds (the input to servings scaling). Three options:

| Option | Shape | Comment |
|---|---|---|
| **M1. `meal_plan` smart_markdown diagram** | Markdown document with `{{meal:<recipe-diagram-id>:diners:6}}` tokens, one per meal. | Same surface as recipes. Reuses smart_markdown grammar. Simplest. |
| M2. New `meal_plan` diagram type | Bespoke diagram type with structured rows (date, recipe, diners). | More UI work; better for calendar-style views; not needed for v1. |
| M3. Package of references | A package whose elements each carry `data: {recipe_id, diners}`. | Awkward — packages are organisational, not content. |

**Recommendation: M1.** A meal plan is just a smart_markdown diagram that lists meals with diner counts, e.g.:

```markdown
# Week of 26 May

- Mon: {{meal:2b9e8712-…:diners:4}}  <!-- Spaghetti -->
- Tue: {{meal:abc-…:diners:6}}        <!-- Cottage Pie -->
- Wed: ...
```

The token resolves at read time to `"Spaghetti (serves 4)"` etc. — and the aggregator picks the same token to know which recipes to walk and at what scale.

This adds one more entity-type variant (`meal`) to the smart_markdown token grammar, alongside `ingredient` from §4. Both extensions land in the same ADR.

---

## 6. The shopping-list surface

Per user's Q2 selection: **Dynamic List diagram (extended).** Two implementation flavours:

| Flavour | Description |
|---|---|
| **F1. New `shopping_list` diagram type** *(recommended)* | New diagram type registered under the existing `markdown` notation, computed by a new `compute_shopping_list_content` module. Source: meal-plan diagram id. Output: grouped, aggregated markdown. |
| F2. New mode of existing `dynamic_list` | Add a third `mode` to `data.dynamic_source`: `meal_plan_aggregation`, with `meal_plan_diagram_id`. Shares the ADR-186 surface. |

F1 is preferred because the logic — walking diagrams, parsing tokens, scaling, summing, grouping by aisle — is materially different from ADR-186's dynamic_list which only enumerates elements/relationships. Bundling it as a `dynamic_list` mode would blur the existing semantics. A separate diagram type keeps the synth-on-read pattern but with a focused algorithm.

### 6.1 Compute algorithm (the v1 contract)

Inputs:
- `data.shopping_list_source.meal_plan_diagram_id: <uuid>`
- `data.shopping_list_source.group_by: "aisle" | "none"` (default `"aisle"`)
- `data.shopping_list_source.show_recipe_breakdown: true | false` (default `true`)

Algorithm:

```
1. Read meal-plan diagram's markdown_source.
2. Extract every {{meal:<recipe-diag-id>:diners:M}} token.
   For each:
     2a. Load recipe diagram's markdown_source.
     2b. Extract recipe's data.servings (N) from the recipe diagram's data
         blob (or from a {{recipe:self:servings:N}} convention).
     2c. scale := M / N
     2d. Extract every {{ingredient:<elem-id>:qty:Q[:unit:U]}} from recipe.
         For each: ingredient_lines.append((elem_id, U or default_unit, Q * scale, recipe_name))
3. Group ingredient_lines by elem_id. Within a group:
   - Same-unit sum: group by unit, sum qtys (user-confirmed Q3).
   - If multiple units in the same element group, emit one line per unit
     (no cross-unit conversion; user-confirmed Q3).
4. Resolve elem_id -> element (name, package_name = aisle).
5. Group elements by aisle (package_name). Sort aisles in canonical order;
   sort items within aisle alphabetically.
6. Emit markdown:

   ## Produce
   - Carrots — 3 (Bolognese 1, Cottage Pie 2)
   - Potato — 1 kg (Cottage Pie 1 kg)

   ## Meat & Poultry
   - Pork mince — 1 kg (Bolognese 500 g + Cottage Pie 500 g)

   ## Pantry
   ...
```

### 6.2 Edge-case handling

| Case | v1 behaviour |
|---|---|
| Ingredient appears with no `qty:` token (e.g., `{{element:UUID:name}}` "a pinch of salt") | Listed once, no quantity, with a `(unspecified)` marker. The user can pin canonical defaults later. |
| Mixed units on same ingredient (e.g., 500 g + 1 kg) | Two lines: `500 g` and `1 kg`. Unit normalisation is out of scope (user-confirmed). |
| Recipe missing `servings` | Treated as `servings = diners` (i.e., scale = 1). Warning marker in the rendered output. |
| Unresolvable element | Rendered as `~~Unknown ingredient~~` per ADR-205's strikethrough convention. |
| Element with no `attributes/Unit/type` | The token-level `unit:` override wins; otherwise rendered without a unit and grouped under "(no unit)". |

### 6.3 Why this is "not brittle"

1. **Quantities are structured tokens, not parsed natural language.** No regex over "half a cup", no "g" vs "grams" confusion.
2. **Element identity is by UUID, not name.** Renaming "Pork mince" → "Pork mince (free range)" doesn't break aggregation.
3. **Synth-on-read.** No stored/stale shopping list to keep in sync with changing recipes; every read recomputes.
4. **Same renderer pipeline** (md → docx → pdf) as every other markdown diagram. No new rendering code.
5. **Surface parity is automatic** (CI-enforced): the create/update endpoint is just a diagram create with `diagram_type = "shopping_list"`, picked up by the existing write parity check.

---

## 7. AI integration (the demo glue)

The end-to-end vision is *"take a photo of the jotter pad → meal plan appears in Iris."* That step is AI-assisted, not part of this feature's core, but the design needs to compose with it.

The natural decomposition:

1. **Photo → meal plan diagram** (Ask AI + existing creation prompts). The user's photo and a system prompt that explains the `{{meal:<recipe-id>:diners:M>}}` grammar lets Claude write the meal-plan smart_markdown. The recipe-name → recipe-id resolution piggy-backs on the existing `/api/search/entities` endpoint that ADR-206 added for the smart_markdown picker.
2. **Meal plan → shopping list** = pure compute (the §6 algorithm). No AI needed.
3. **Shopping list → Woolworths trolley** = existing proven path (Claude Chrome extension + the grocery elements' `attributes/Products/[Preferred product]` attribute that already maps to Woolworths SKUs).

A `response_format` prompt for "Shopping list" (ADR-157 cascade) is **not** required for the core feature — but it could be added later as a fallback path: "Ask AI: given these recipes and diners, write a shopping list" using the same grammar. Belt-and-braces redundancy, not v1 scope.

---

## 8. Recommended minimum-viable scope

In ADR/spec-able terms:

| Item | Adds |
|---|---|
| **ADR-N1** | Two new smart_markdown token variants: `{{ingredient:<element-id>:qty:<number>[:unit:<unit>]}}` and `{{meal:<recipe-diagram-id>:diners:<number>}}`. Both extend ADR-205's grammar without changing the resolver dispatch shape. |
| **ADR-N2** | New diagram type `shopping_list` under the `markdown` notation. Synth-on-read. Source diagram id + grouping config. Spec defines the §6.1 algorithm and §6.2 edge cases as the contract. |
| **ADR-N3** (optional, v1.1) | Add a `data.servings: <number>` convention on recipe diagrams (no schema change — `diagram.data` is already a free JSON blob). Document the convention so AI-driven recipe creation populates it. |
| **Migration** | One-shot script that finds the current "`NNN {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}`" pattern across all 34 recipes and rewrites as `{{ingredient:UUID:qty:NNN}}`. Backed by tests; idempotent; reversible (the new token still resolves to the same rendered output). |
| **Surface parity** | Pure additions to existing surfaces — `diagram_type = "shopping_list"` rides on the existing diagram CRUD, satisfying the CI check automatically. |
| **MCP** | Two new tools beyond the diagram CRUD: (a) `generate_shopping_list(meal_plan_diagram_id, group_by="aisle")` for ad-hoc rendering without persisting a diagram; (b) `create_meal_plan_from_image(image_bytes, week_label)` (Ask AI under the hood). Both are convenience wrappers; the core feature works without them. |
| **CLI** | `iris shopping-list <meal-plan-diagram-id>` — wraps the MCP tool. |

### What we are *not* doing in v1

- Unit normalisation (g ↔ kg, ml ↔ l, cups ↔ ml).
- Pantry deduction.
- Recurring meal plans / templates.
- Cost estimation.
- Bringing recipes into the Knowledge Graph as elements (Path A from §4).

These are all clean extensions on top of the v1 surface, not blockers for it.

---

## 9. Risks and open questions

| Risk | Mitigation |
|---|---|
| Token grammar drift between recipe authoring UI (smart_markdown picker) and aggregator | Define the token regex once in `smart_markdown.py` and import from `shopping_list.py`. Single source of truth. Tests cover both producers. |
| Migration script corrupts existing recipes | Dry-run mode + diff output + revert script. Tests on a copy of the UAT database. |
| "Servings" convention isn't followed consistently across recipes | Scale defaults to 1 (i.e., quantities pass through) when `servings` is missing. Warning visible in rendered output to nudge the user. |
| Future need for unit conversion (the rejected Q3 option) | A new ADR can add a unit-family registry on the grocery elements (`attributes/Unit/canonical: "g"`) and a converter — purely additive to v1. |
| Multiple-product grocery items (e.g., Pork mince has 2 Woolworths SKUs) | Already modelled via `Products[*]` + `Preferred product` attributes; the shopping list emits the ingredient name + qty, and the downstream Chrome extension picks the SKU. v1 does nothing new here. |

### Open questions worth answering before drafting the ADR

1. **Token naming.** Is `{{ingredient:…}}` the right entity-type variant, or do you prefer `{{element:…:qty:N}}` (extending the existing `element` variant with a new field-spec rather than introducing a new variant)? Both work; the latter is a tighter grammar diff but conflates "render an element field" with "render an ingredient line."
2. **Meal-plan recipe references — `{{meal:<recipe-diagram-id>:…}}` vs `{{diagram:<recipe-diagram-id>:…}}`.** `diagram` is already in ADR-205's grammar. The `meal` name is more readable; the `diagram` name is grammar-conservative. Pick one.
3. **Where does the meal plan live?** A package in the `Meal plans` set called `Weekly meal plans` (with one smart_markdown diagram per week)? A separate `Meal plans` collection? Naming and place affect discoverability but not the design.
4. **Migration timing.** Land the new token variant first, then the migration of the 34 recipes, then the `shopping_list` diagram type? Or land all three behind a single feature branch and demo it end-to-end? My preference is the staged route (each lands with its own tests and ADR), but the demo motivation might favour the single-branch route.

---

## 10. Recommendation summary (one paragraph)

Add two structured token variants to `smart_markdown` — `{{ingredient:<id>:qty:N}}` and `{{meal:<recipe-id>:diners:M}}` — so quantities and diner counts live in machine-parseable tokens while preserving the existing recipe-as-document UX. Model a meal plan as a `smart_markdown` diagram listing meal tokens. Add a new `shopping_list` diagram type (synth-on-read) that walks the meal plan, scales each recipe by diners/servings, sums quantities per ingredient by element id with same-unit-only aggregation, groups output by aisle (using the existing `Groceries`-set package = aisle convention), and renders aggregated markdown that the same docx/pdf/MCP/CLI pipeline serves to Claude Desktop or the Chrome extension unchanged. Migrate the 34 existing recipes in a one-shot script. This composes with everything Iris already does (synth-on-read diagrams, smart_markdown tokens, surface parity, batch tools, artefacts) and adds no new architectural primitives. It honours both functional requirements (R1 cross-recipe sum, R2 servings scaling) and the "not brittle" architectural requirement (R3) by making quantities first-class structured data rather than parsed natural language.
