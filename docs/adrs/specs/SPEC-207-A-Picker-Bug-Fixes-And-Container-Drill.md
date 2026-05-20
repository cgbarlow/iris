# SPEC-207-A: Picker bug fixes + container drill implementation

Implements: [ADR-207](../ADR-207-Picker-Bug-Fixes-And-Container-Drill.md)
Status: Living

## Search regression fix

In `frontend/src/lib/canvas/text/SmartMarkdownSlashPicker.svelte`:

Remove:

```svelte
$effect(() => {
    if (mode === 'browse') scheduleSearch();
});
```

Add `oninput={scheduleSearch}` to the browse input element. Initial load on
mode change continues to fire via the existing `await loadBrowse()` in
`onMount` and after each navigation.

## Drill keystroke fix

In `handleDrillKey`:

```ts
if (e.key === '.' || e.key === 'Tab') {
    e.preventDefault();
    const menu = drillMenuItems;
    if (menu.length > 0) {
        chooseDrillItem(menu[Math.min(drillIdx, menu.length - 1)]);
    }
    return;
}
if (e.key === 'Enter') {
    const menu = drillMenuItems;
    if (menu.length > 0) {
        e.preventDefault();
        chooseDrillItem(menu[Math.min(drillIdx, menu.length - 1)]);
    }
    return;
}
```

Tab and `.` are unconditionally consumed; Enter only when there's something
to act on (so a user can still submit a form-style Enter if the menu is
genuinely empty).

## Container drill for non-elements

`enterDrill` becomes:

```ts
async function enterDrill(entity: EntitySearchResult) {
    chosenEntity = entity;
    drillPath = [];
    drillFilter = '';
    drillIdx = 0;
    mode = 'drill';
    drillNode = null;
    if (entity.entity_type === 'element') {
        await fetchDrillNode();
    } else {
        await fetchContainerDrillNode(entity);
    }
    await tick();
    drillInputEl?.focus();
}
```

`fetchContainerDrillNode` issues a `/api/picker/browse` call appropriate
for the entity type and translates the response into a synthetic
`TreeDescriptor` with `kind: 'dict'` and a `keys` array. The keys are:

- `name`, `description` (always)
- For collections: each set name as a child key
- For sets: each non-zero bucket label (`Elements`, `Packages`, `Views`)
- For packages: each contained element name (and diagram name if present)

The picker's `chooseDrillItem` already drills into the highlighted item
when it has `kind: 'container'`. Containers fetched from a child-entity
call set `chosenEntity` to that child and recurse via `enterDrill`.

### Backend extension

`backend/app/search/router.py` — add `scope=package` and
`scope=package_bucket` to `/api/picker/browse`:

```
GET /api/picker/browse?scope=package&package_id=<guid>
  → items: contained elements; counts: { elements: N }
GET /api/picker/browse?scope=package_bucket&package_id=<guid>&entity_type=element
  → items: elements with that package_id
```

Breadcrumb gains a `scope: 'package'` step. Picker logic skips the bucket
intermediary if only one bucket has non-zero count (so a package with
elements but no diagrams shows elements directly).

## Pick-this shortcut in browse mode

At non-root breadcrumb levels, render at the top of the items list:

```svelte
<li class="slash-picker__item slash-picker__item--pick"
    onclick={() => enterDrill(breadcrumbLeafEntity())}>
    <span>Pick this {breadcrumbLeafLabel()}</span>
</li>
```

Where `breadcrumbLeafEntity()` synthesizes an `EntitySearchResult` from
the breadcrumb's last step:

```ts
function breadcrumbLeafEntity(): EntitySearchResult | null {
    const last = breadcrumb[breadcrumb.length - 1];
    if (!last.scope || !last.id) return null;
    return {
        id: last.id,
        entity_type: last.scope === 'collection' ? 'collection'
                   : last.scope === 'set' ? 'set'
                   : last.scope === 'package' ? 'package'
                   : 'element', // set_bucket entries don't reach here
        name: last.label,
    };
}
```

Hidden at the root level (no entity to pick).

## Diagram → View label inside the picker

Two replacements inside `SmartMarkdownSlashPicker.svelte`:

1. The bucket label string `'Diagrams'` (currently set in `clickBucket`)
   → `'Views'`.
2. Badge text: introduce a tiny mapper `displayType(t)`:

```ts
function displayType(t: EntityType): string {
    return t === 'diagram' ? 'view' : t;
}
```

Used in two places: the `<span class="slash-picker__badge ...">{r.entity_type}</span>`
template and the breadcrumb step labels for `set_bucket`. Backend continues
to send `entity_type='diagram'` — no API change.

## Badge colour rotation

In the `<style>` block:

```css
.slash-picker__badge--collection { background: #fce7f3; color: #831843; }
.slash-picker__badge--set        { background: #f3e8ff; color: #581c87; }
.slash-picker__badge--package    { background: #fef3c7; color: #92400e; }
.slash-picker__badge--diagram    { background: #dcfce7; color: #14532d; }
.slash-picker__badge--element    { background: #dbeafe; color: #1e3a8a; }
```

(Foreground colours follow the same rotation so contrast pairs stay
in their families.)

## 'New' button height fix

In `frontend/src/lib/components/HierarchyControls.svelte`:

```svelte
<button class="... border border-transparent ..."
        style="background-color: var(--color-primary)">
    + New
</button>
```

The `border border-transparent` makes the box model match the 'Show'
button's solid `border border-color: var(--color-border)` without
showing a visible border.

## Verification

1. **Search**: open the picker in a Smart Markdown view, type any
   substring → results appear (e.g. "mince" → "pork mince").
2. **Drill Tab/`.`**: pick any element, in the drill strip press Tab on
   highlighted container → drills. Press `.` on highlighted container
   → drills. Letters narrow the menu. Enter on primitive inserts.
3. **Container drill**: pick a package (e.g. "Pantry Items") → drill
   menu shows `name`, `description`, and a row for each contained
   element. Clicking an element drills into it.
4. **Pick-this**: navigate to a set in browse mode → see "Pick this
   {set name}" at the top of the items list. Clicking enters drill
   mode for the set.
5. **Badge colours**: collection rows pale pink, set rows pale purple,
   package rows pale amber, view rows pale green (label "view"),
   element rows pale blue. Bucket label says "Views".
6. **'New' button**: same height as 'Show' (pixel-perfect).
