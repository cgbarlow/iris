# SPEC-211-b: Smart-markdown picker — Stamps section

Implements: [ADR-211](../ADR-211-Element-Template-Stamps.md) — the deferred picker UI from SPEC-211-a §4.

## 1. Behaviour

When the smart-markdown picker enters drill mode against an `element`
entity, it fetches in-scope stamps via:

```
GET /api/element-templates/stamps?element_id=<element-id>
```

(unchanged endpoint from v6.19.0). The response is the list of stamps
whose scope (global or set-matching) and `element_type` filter (if
captured) admit the element. Each `markdown_stamp` has `{{self:…}}`
already substituted with `{{element:<element-id>:…}}` so the body is
paste-ready.

Returned stamps render as one-pick rows at the top of the drill menu,
above the existing image / name / description / attributes-tree
entries. Selecting one emits the stamp body verbatim via `oninsert`.

For non-element entities (collection, set, package, diagram), stamps
don't apply (the endpoint requires an element id); the picker shows
the existing menu unchanged.

## 2. Data flow

```
user picks element in browse → enterDrill(entity)
  ├─ fetchDrillNode()          (existing element data-tree fetch)
  ├─ fetchAttachedImages(entity) (existing ADR-209)
  └─ fetchAttachedStamps(entity) (NEW)
         GET /api/element-templates/stamps?element_id=<id>
         → attachedStamps state

drillMenuItems $derived adds stamp items at the top of the menu
chooseDrillItem(stamp) → oninsert(stamp.markdown_stamp)
```

## 3. UI

Stamp rows display as `Stamp: <template name>`. Keyboard navigation
(arrows, Enter, Tab, `.`) inherits from the existing drill menu — no
new keys.

The fillable-slot Shift+Enter shortcut from ADR-210 / SPEC-210-a
**does not apply** to stamp picks: the stamp body authors its own
fillable-slot markers (`...path=`) and we don't post-process them.

## 4. Test

`frontend/tests/unit/pickerStampsSection.test.ts` covers:

- The `/api/element-templates/stamps` response shape.
- Empty-list / no-stamps degrades gracefully.
- The stamp insert contract: body emitted verbatim via `oninsert`.
- Fillable-slot markers (`...=}}`) are preserved.
- Scope-filter contract (global stamps surface broadly; set-scoped
  stamps only for the matching set).

Per the project's frontend testing posture, these are data-shape +
business-rule tests, not full component renders.

## 5. Out of scope

- Inline preview of the stamp before picking it (would require an
  extra render pass; v1 trusts the template name).
- "Manage stamps" link in the picker footer (deferred to v6.19.2's
  stamp editor).
