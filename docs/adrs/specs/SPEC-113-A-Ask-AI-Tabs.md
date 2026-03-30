# SPEC-113-A: Ask AI Tabbed Layout

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-113-A |
| **ADR** | [ADR-113](../ADR-113-Ask-AI-Tabbed-Layout.md) |
| **Status** | Draft |
| **Date** | 2026-03-29 |

---

## Overview

Split the Ask AI page into two local tabs — **Context** and **Request** — to maximise vertical space for the chat dialogue while keeping context selectors accessible.

## Tab Bar

- Two tabs: "Context" and "Request"
- Uses `<button>` elements with `role="tab"` and `aria-selected` attributes
- Styling matches Admin/Settings tabs: `px-5 py-2 text-sm font-medium`, `border-bottom: 2px solid`, `margin-bottom: -1px`
- Active tab: `var(--color-primary)` text and border; inactive: `var(--color-muted)` text, transparent border
- Local state toggling via `$state` (not URL-routed)

## Context Tab

Contains all context selectors (moved from current stacked layout):

1. **Collection dropdown** — filters sets by collection, auto-selects active collection
2. **MultiSetSelector** — multi-select with package drill-down
3. **DocRefSelector** — shown only when DocRef extension is enabled; enhanced with `ondocuments` callback to expose document metadata to the page

## Request Tab

1. **Context summary line** — single line above the chat showing selected set names and document titles, comma-separated, truncated with ellipsis (`truncate` class + `title` attribute)
2. **SetQA component** — fills all remaining vertical space (`flex-1`); keyed on `contextKey` to re-render when selected context changes
3. When no context is selected: shows a prompt directing users to the Context tab

## Panel Toggling

- Uses `display:none` (not `{#if}`) to hide inactive panel
- Preserves SetQA chat state (messages, scroll position, streaming state) across tab switches
- Hidden panel does not participate in flexbox layout, so Request tab gets full `flex-1` height

## DocRefSelector Enhancement

New optional prop:

```typescript
ondocuments?: (docs: { id: string; title: string }[]) => void;
```

Called after documents load in `loadDocuments()`. Enables the page to build the context summary line without a duplicate API call (DRY).

## Files

| File | Change |
|------|--------|
| `frontend/src/routes/ask/+page.svelte` | Add tab state, tab bar, two panels, context summary |
| `frontend/src/lib/components/DocRefSelector.svelte` | Add optional `ondocuments` callback prop |

## Acceptance Criteria

1. Two tabs render with correct Settings-style styling
2. Context tab: collection dropdown, set selector, DocRef selector all functional
3. Request tab: summary line shows selected context comma-separated
4. Chat fills full available vertical space on Request tab
5. Switching tabs preserves chat state (messages, scroll, streaming)
6. Changing context on Context tab triggers SetQA re-render on Request tab
7. No context selected: Request tab shows guidance message
8. No `{@html}` without DOMPurify sanitisation
