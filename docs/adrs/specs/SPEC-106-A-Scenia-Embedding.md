# SPEC-106-A: Scenia Embedding

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-106-A |
| **ADR** | [ADR-106](../ADR-106-Scenia-React-Embedding.md) |
| **Status** | Draft |
| **Date** | 2026-03-25 |

---

## Overview

Scenia React app is embedded in Iris via a patched fork with pluggable persistence, mounted at `/scenia` via `createRoot`. An Iris-native data view lives at `/roadmap`.

## 1. Fork Patches

The Scenia fork (cgbarlow/waylonkenning_scenia) receives the following patches:

### db.ts Adapter

Replace the hardcoded IndexedDB implementation with a pluggable adapter interface:

```typescript
export interface DbAdapter {
  getAppData(): Promise<AppData>;
  saveAppData(data: AppData): Promise<void>;
}

let adapter: DbAdapter | null = null;

export function setDbAdapter(ext: DbAdapter) {
  adapter = ext;
}
```

When `adapter` is set, all `getAppData`/`saveAppData` calls delegate to it instead of IndexedDB.

### embed.tsx

New entry point that exports a mount function for external consumers:

```typescript
export function mountScenia(
  container: HTMLElement,
  adapter: DbAdapter
): () => void {
  setDbAdapter(adapter);
  const root = createRoot(container);
  root.render(<App />);
  return () => root.unmount();
}
```

Returns a cleanup function for lifecycle management.

### Library Build

Add a Vite library build config that outputs an ES module:

```
dist/
├── scenia.es.js
├── scenia.css
└── types/
```

Iris installs the fork via `npm install cgbarlow/waylonkenning_scenia`.

### CSS Scoping

All Scenia Tailwind classes are scoped under a `.scenia-root` container class to avoid conflicts with Iris's own Tailwind configuration. Theme variables (colors, spacing) are namespaced with `--scenia-` prefix.

### Skip Landing Page

The embed entry point bypasses Scenia's landing/onboarding page and renders the main application view directly.

## 2. Route Layout

| Route | Component | Description |
|-------|-----------|-------------|
| `/scenia` | `SceniaEmbed.svelte` | Full React Scenia app mounted via `createRoot` |
| `/roadmap` | `RoadmapView.svelte` | Iris-native data view of Scenia roadmap data |

### SceniaEmbed.svelte

```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { mountScenia } from 'scenia/embed';
  import { createIrisAdapter } from '$lib/scenia/adapter';

  let container: HTMLDivElement;
  let cleanup: (() => void) | null = null;

  onMount(() => {
    const adapter = createIrisAdapter();
    cleanup = mountScenia(container, adapter);
  });

  onDestroy(() => {
    cleanup?.();
  });
</script>

<div bind:this={container} class="scenia-root h-full w-full" />
```

### RoadmapView.svelte

Iris-native Svelte component that fetches Scenia data from `/api/scenia/data` and renders it as a read/browse view with navigation to `/scenia` for full editing.

## 3. Adapter Enhancement

### transforms.ts

Conversion layer between Iris API responses and Scenia's native types:

```typescript
export function irisToScenia(apiData: IrisSceniaResponse): AppData {
  // Convert Iris elements (element_type: "scenia_*") to Scenia native types
  // Map relationships to Scenia cross-references
  // Reconstruct timeline settings, versions, asset categories
}

export function sceniaToIris(appData: AppData): IrisSceniaPayload {
  // Convert Scenia native types back to Iris element format
  // Preserve element IDs for update-vs-create detection
  // Map cross-references to Iris relationships
}
```

### Iris Adapter Implementation

```typescript
export function createIrisAdapter(): DbAdapter {
  return {
    async getAppData() {
      const res = await fetch('/api/scenia/data');
      const irisData = await res.json();
      return irisToScenia(irisData);
    },
    async saveAppData(data: AppData) {
      const payload = sceniaToIris(data);
      await fetch('/api/scenia/data', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    },
  };
}
```

## 4. Navigation

### Sidebar

- "Roadmap" item added to the main sidebar navigation, linking to `/roadmap`
- When the Scenia extension is disabled, the sidebar item is hidden

### Cross-Links

- `/roadmap` includes a "View in Scenia" button linking to `/scenia`
- Individual roadmap items in the data view include "View in Scenia" buttons that deep-link to the relevant entity in the Scenia app
- All cross-link buttons consistently use the text "View in Scenia"

## 5. Seed Data

Seed data matches the content from Scenia's `demoData.ts`, providing a realistic starting dataset:

- ~100+ entities across all Scenia entity types (initiatives, milestones, features, tasks, etc.)
- 10 interlinked diagrams generated from the seed data
- Cross-references between entities to demonstrate relationship capabilities
- Timeline settings with realistic date ranges
- Multiple asset categories and application statuses

The seed data is loaded when the Scenia extension is first installed via the extensions admin UI.

## Acceptance Criteria

1. Scenia React app loads at `/scenia` with data from Iris API
2. Data edits in Scenia persist to Iris database
3. `/roadmap` shows live data view with "View in Scenia" button
4. All cross-links use "View in Scenia" text
5. Seed data matches Scenia's `demoData.ts` content
6. 10 interlinked diagrams generated from seed data
