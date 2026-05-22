# SPEC-211-e: Clone-from-existing for element templates

Implements: extension of [SPEC-211-a](./SPEC-211-a-Element-Template-Stamps.md). Addresses observation C4 from the [2026-05-22 issue #211 comment exchange](https://github.com/cgbarlow/iris/issues/211).

## 1. UX

`TemplatesListDialog.svelte` (the dialog opened by the "Templates" button on the elements list) gains a **Clone** button per row, next to the existing **Use** button.

- **Use** (existing) — creates a new *element* from the template.
- **Clone** (new) — creates a new *template* from the source template, prefilled with the source's `name + " (copy)"`, `description`, `template_data`, and `markdown_stamp`.

On Clone, the dialog closes and the elements page surfaces a small inline mini-dialog asking for the new template name (defaulted to `<source> (copy)`). On submit:

```
POST /api/element-templates
{
  name: "<user-entered>",
  description: <source.description>,
  template_data: <source.template_data>,
  markdown_stamp: <source.markdown_stamp>,
  is_global: <source.is_global>,
  set_id: source.is_global ? null : <currentSetId>
}
```

After success, the page navigates to `/element-templates/<new-id>` so the user can edit further (e.g. adjust the stamp body).

## 2. Why a mini-dialog, not a full create form

The existing `CreateTemplateDialog` is built around the "snapshot from element" path (it requires `sourceElementId`). The clone case is structurally different — no source element, just a source template. Rather than complicating CreateTemplateDialog with a clone mode, the elements list hosts a tiny inline form for the rename. Implementation footprint stays small.

## 3. State additions

`elements/+page.svelte` gains:

```ts
let cloneSource = $state<CloneSource | null>(null);
let cloneNewName = $state('');
let cloneSubmitting = $state(false);
let cloneError = $state<string | null>(null);

function startCloneTemplate(source: CloneSource) { ... }
function cancelCloneTemplate() { ... }
async function confirmCloneTemplate(event: SubmitEvent) { ... }
```

`TemplatesListDialog` gains an optional `onclone: (source: ElementTemplate) => void` prop — emitted on Clone-button click. The button only renders when `onclone` is provided (so other callers of TemplatesListDialog, if any future ones, don't gain the button by accident).

## 4. Backend

Unchanged. The existing `POST /api/element-templates` endpoint accepts the body shape (ADR-211 §"source-element optionality"). No new MCP / CLI parity needed — same write surface as today.

## 5. Tests

`frontend/tests/unit/elementTemplateClone.test.ts` covers the clone body construction:

- Body includes `markdown_stamp` when the source has one.
- Body's `is_global` matches the source.
- Body's `set_id` is `null` when the source is global; equals current set id otherwise.
- Default name is `"<source> (copy)"`.

## 6. Genericness (ADR-214)

UI logic only — no domain terminology. Clean.
