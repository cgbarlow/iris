# SPEC-050-A: Tag Autocomplete

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-050-A |
| **ADR Reference** | [ADR-050: Tag Autocomplete](../ADR-050-Tag-Autocomplete.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details the addition of autocomplete functionality to the existing `TagInput` component. A new `suggestions` prop provides a list of known tags, which are filtered as the user types and presented in a dropdown. Keyboard navigation (ArrowDown, ArrowUp, Enter, Escape) and ARIA combobox semantics ensure accessibility compliance.

---

## A. TagInput Props Extension

### New Props

**File:** `src/lib/components/TagInput.svelte`

```typescript
interface Props {
    // ... existing props ...
    tags: string[];
    onadd?: (tag: string) => void;
    onremove?: (tag: string) => void;
    // New autocomplete props (WP-10)
    suggestions?: string[];
}
```

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `suggestions` | `string[]` | `[]` | List of known tags to suggest during typing |

The `suggestions` prop is optional. When not provided (or empty), the component behaves exactly as before with no autocomplete dropdown.

---

## B. Filtered Suggestions

### Derived State

```typescript
let inputValue = $state('');
let showSuggestions = $state(false);
let selectedIndex = $state(-1);

const filteredSuggestions = $derived.by(() => {
    if (!suggestions || suggestions.length === 0 || !inputValue.trim()) {
        return [];
    }
    const query = inputValue.trim().toLowerCase();
    return suggestions.filter(
        (s) =>
            s.toLowerCase().includes(query) &&
            !tags.includes(s) // Exclude already-added tags
    );
});
```

### Filtering Rules

- Suggestions are filtered case-insensitively using substring matching (`includes`)
- Tags already added to the input are excluded from suggestions
- An empty or whitespace-only input produces no suggestions
- If no suggestions match, the dropdown is hidden

---

## C. Dropdown UI

### Markup

```svelte
<div class="tag-input-wrapper" role="combobox" aria-expanded={showSuggestions && filteredSuggestions.length > 0} aria-haspopup="listbox" aria-owns="tag-suggestions">
    <!-- Existing tag chips -->
    {#each tags as tag}
        <span class="tag-chip">
            {tag}
            <button onclick={() => onremove?.(tag)} aria-label="Remove tag {tag}">x</button>
        </span>
    {/each}

    <!-- Input -->
    <input
        type="text"
        bind:value={inputValue}
        oninput={handleInput}
        onkeydown={handleKeydown}
        onfocus={() => showSuggestions = true}
        onblur={handleBlur}
        role="combobox"
        aria-autocomplete="list"
        aria-controls="tag-suggestions"
        aria-activedescendant={selectedIndex >= 0 ? `tag-suggestion-${selectedIndex}` : undefined}
    />

    <!-- Suggestions dropdown -->
    {#if showSuggestions && filteredSuggestions.length > 0}
        <ul id="tag-suggestions" role="listbox" class="suggestions-dropdown">
            {#each filteredSuggestions as suggestion, i}
                <li
                    id="tag-suggestion-{i}"
                    role="option"
                    aria-selected={i === selectedIndex}
                    class="suggestion-item"
                    class:selected={i === selectedIndex}
                    onpointerdown|preventDefault={() => selectSuggestion(suggestion)}
                >
                    {suggestion}
                </li>
            {/each}
        </ul>
    {/if}
</div>
```

### Dropdown Styling

```css
.suggestions-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    z-index: 10;
    list-style: none;
    margin: 4px 0 0 0;
    padding: 0;
}

.suggestion-item {
    padding: 6px 10px;
    cursor: pointer;
    font-size: 0.875rem;
}

.suggestion-item:hover,
.suggestion-item.selected {
    background: var(--color-primary);
    color: white;
}
```

---

## D. Keyboard Navigation

### Key Bindings

```typescript
function handleKeydown(e: KeyboardEvent) {
    if (showSuggestions && filteredSuggestions.length > 0) {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, filteredSuggestions.length - 1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                break;
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < filteredSuggestions.length) {
                    selectSuggestion(filteredSuggestions[selectedIndex]);
                } else if (inputValue.trim()) {
                    addTag(inputValue.trim());
                }
                break;
            case 'Escape':
                showSuggestions = false;
                selectedIndex = -1;
                break;
        }
    } else if (e.key === 'Enter' && inputValue.trim()) {
        e.preventDefault();
        addTag(inputValue.trim());
    }
}
```

| Key | Behaviour |
|-----|-----------|
| ArrowDown | Move selection to next suggestion (clamped at end) |
| ArrowUp | Move selection to previous suggestion (clamped at -1 = none) |
| Enter | Accept selected suggestion, or add free-text tag if no selection |
| Escape | Close dropdown, reset selection index |

### Selection Helper

```typescript
function selectSuggestion(suggestion: string) {
    onadd?.(suggestion);
    inputValue = '';
    selectedIndex = -1;
    showSuggestions = false;
}

function addTag(tag: string) {
    if (!tags.includes(tag)) {
        onadd?.(tag);
    }
    inputValue = '';
    selectedIndex = -1;
}

function handleInput() {
    showSuggestions = true;
    selectedIndex = -1;
}

function handleBlur() {
    // Delay to allow click on suggestion
    setTimeout(() => {
        showSuggestions = false;
        selectedIndex = -1;
    }, 150);
}
```

---

## E. ARIA Combobox Support

### Roles and Properties

| Element | Role | ARIA Attributes |
|---------|------|-----------------|
| Wrapper `<div>` | `combobox` | `aria-expanded`, `aria-haspopup="listbox"`, `aria-owns` |
| Text `<input>` | `combobox` | `aria-autocomplete="list"`, `aria-controls`, `aria-activedescendant` |
| Dropdown `<ul>` | `listbox` | `id` matching `aria-controls` |
| Suggestion `<li>` | `option` | `aria-selected`, unique `id` for `aria-activedescendant` |

### Screen Reader Behaviour

- When the dropdown opens, `aria-expanded="true"` announces the expanded state
- As the user arrows through suggestions, `aria-activedescendant` updates to the focused option's ID, causing the screen reader to announce the suggestion text
- When a suggestion is selected, the dropdown closes and `aria-expanded` returns to `false`

---

## F. Suggestion Data Source

### Where Suggestions Come From

The parent component is responsible for fetching and passing the `suggestions` array. For entity tags, the existing `GET /api/entities/tags` endpoint (or equivalent) provides all known tags:

```typescript
// In parent component
let allTags = $state<string[]>([]);

$effect(() => {
    apiFetch<string[]>('/api/entities/tags')
        .then((tags) => { allTags = tags; })
        .catch(() => { allTags = []; });
});
```

```svelte
<TagInput
    tags={entityTags}
    suggestions={allTags}
    onadd={handleTagAdd}
    onremove={handleTagRemove}
/>
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Suggestions dropdown appears on typing | Type in tag input; verify dropdown with matching suggestions |
| Suggestions filtered case-insensitively | Type "EXA"; verify "example" appears in suggestions |
| Already-added tags excluded from suggestions | Add "iris" tag; verify "iris" not in dropdown |
| Empty input shows no suggestions | Clear input; verify dropdown hidden |
| ArrowDown moves selection down | Press ArrowDown; verify next item highlighted |
| ArrowUp moves selection up | Press ArrowUp; verify previous item highlighted |
| Enter accepts selected suggestion | Arrow to suggestion, press Enter; verify tag added |
| Enter with no selection adds free-text tag | Type new tag, press Enter; verify tag added |
| Escape closes dropdown | Press Escape; verify dropdown hidden |
| Click on suggestion adds tag | Click suggestion item; verify tag added |
| `aria-expanded` reflects dropdown state | Open/close dropdown; verify attribute changes |
| `aria-activedescendant` tracks selection | Arrow through suggestions; verify attribute updates |
| `role="listbox"` on dropdown | Inspect dropdown element; verify role |
| `role="option"` on suggestion items | Inspect list items; verify role |
| Component works without suggestions prop | Render without `suggestions`; verify standard tag input behaviour |
| Dropdown scrolls for long lists | Provide 20+ suggestions; verify scrollable dropdown |

---

*This specification implements [ADR-050](../ADR-050-Tag-Autocomplete.md).*
