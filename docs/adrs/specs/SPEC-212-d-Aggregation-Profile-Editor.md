# SPEC-212-d: Aggregation profile editor (UI)

Implements: [ADR-212](../ADR-212-Aggregation-Profiles-And-Engine.md) — the deferred admin / set-editor UI from ADR-212 + the plan's §9.4.

## 1. Component

New `frontend/src/lib/components/AggregationProfileEditor.svelte`:

- **List**: in-scope profiles for the parent (globals or set-scoped) with Name / Scope / Description / Edit / Delete actions.
- **Create / Edit form**: name, description, JSON textarea for `profile_data`, `is_default_for_set` (set-mode only).
- **JSON parse-validate** on Save — invalid JSON keeps the editor open with an inline error.
- **Delete**: confirm dialog → `DELETE /api/aggregation/profiles/{id}` (soft-delete).

Props:

- `setId?: string | null` — when set, list/create produces set-scoped rows.
- `globalsMode?: boolean` — when true, list/create produces `is_global=true` rows.

The component is intentionally pragmatic — a JSON textarea covers v1.

## 2. Why JSON textarea, not a tabbed form

A full tabs-form (General / Traversal / Multiplier / Output) requires:

- Nested form state across multiple sections.
- Conditional rendering for the optional outer-traversal step + multiplier subform.
- Attribute-path inputs that ideally autocomplete against the element data-tree (already supported by the smart-markdown picker but only for live elements; here we're authoring a generic ruleset).
- Validation per field (attribute path syntax, token-type enum, etc.).
- A round-trip from form state → JSON → ProfileData pydantic on the backend without drift.

That's genuinely a multi-day frontend project. The JSON textarea covers the same surface in ~150 lines + parse-validate. The five seeded profiles are good clone templates: users hit "New profile" → paste a seed → edit fields. Form-based editor remains a follow-up.

## 3. Parent integrations

- **`/admin/aggregation-profiles`** new route. Uses `globalsMode={true}`.
- **`/sets/{id}` edit page** — new section before Danger zone, uses `setId={setId}` with `globalsMode={false}`.
- **Admin home (`/admin`)** — new card linking to `/admin/aggregation-profiles`.

The same component covers both contexts. The list filter logic narrows results to the right scope client-side:

- Globals mode → keep `is_global = true` rows only.
- Set mode → keep `is_global = false` AND `set_id == <set>` rows.

(Server returns the union when both are requested; client filters.)

## 4. Request/response shapes

- **List**: `GET /api/aggregation/profiles?set_id=<id?>&include_global=<bool>` → `{items, total, page, page_size}`.
- **Create**: `POST /api/aggregation/profiles` body
  ```json
  {
    "name": "string",
    "description": "string|null",
    "profile_data": { ... },
    "is_default_for_set": false,
    "set_id": "<uuid>|<null>",
    "is_global": true|false
  }
  ```
- **Update**: `PUT /api/aggregation/profiles/{id}` (same shape, partial).
- **Delete**: `DELETE /api/aggregation/profiles/{id}` → 204.

All endpoints shipped in v6.20.0.

## 5. Genericness

The component carries no recipe / meal / ingredient terminology. The list shows whatever names the user creates; the JSON textarea is opaque to the editor — it just round-trips bytes through `JSON.parse` / `JSON.stringify`.

## 6. Test

`frontend/tests/unit/aggregationProfileEditor.test.ts` covers:

- The create/update request body shapes.
- The list filter logic (globals mode vs. set mode).
- JSON parse-validate behaviour.
- The default-profile-template JSON (provided as a clone template) parses against the ProfileData shape.

## 7. Out of scope (future v6.26+)

- Tabbed form-based editor.
- Attribute-path autocomplete.
- Inline preview (calls `POST /api/aggregation/run` against a draft, requires `inline_profile_override` backend support).
- Schema-aware validation beyond JSON syntax.
- Bulk import/export of profiles.
