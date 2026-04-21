# SPEC-122-A: User Guide

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-122-A |
| **ADR** | [ADR-122](../ADR-122-User-Guide.md) |
| **Status** | Approved |
| **Date** | 2026-04-21 |

## Overview

The user guide lives at `/guide` and renders markdown content through
`marked` + DOMPurify (both already in `frontend/package.json`).
Screenshots are produced by a dedicated Playwright project and served
from `frontend/static/guide/`.

## Routes

```
/guide                         → redirects to /guide/getting-started
/guide/getting-started         → first section
/guide/dashboard
/guide/collections-sets
/guide/packages-diagrams
/guide/canvas-editing          (added v4.2.0)
/guide/notations               (added v4.2.0)
/guide/comments                (added v4.2.0)
/guide/knowledge-graph
/guide/search
/guide/ask-ai
/guide/bookmarks
/guide/imports-data            (added v4.2.0)
/guide/roadmap-scenia          (added v4.2.0)
/guide/themes-accessibility    (added v4.2.0)
/guide/keyboard-shortcuts      (added v4.1.3)
/guide/admin                   (now "Admin & Permissions")
```

**Amendment history** — the section list has grown twice since this
spec's original approval:

- **v4.1.3**: `keyboard-shortcuts` added as a dedicated section when
  the `/help` route was merged into the guide and deleted.
- **v4.2.0**: six new sections (`canvas-editing`, `notations`,
  `comments`, `imports-data`, `roadmap-scenia`,
  `themes-accessibility`) added so anonymous visitors can discover
  signed-in-only capabilities, and the existing nine sections
  expanded with deeper content. Sign-in-only material is called out
  inline with a `> **Sign in to use this.**` blockquote rather than
  being hidden from anonymous visitors — matches the ADR-123
  philosophy that the guide serves as a product marketing surface as
  well as a reference.

Implemented as:

- `frontend/src/routes/guide/+layout.svelte` — shared header + left
  navigation bar (list of sections, `use:link` to each).
- `frontend/src/routes/guide/+page.svelte` — root redirect to
  `/guide/getting-started`.
- `frontend/src/routes/guide/[section]/+page.svelte` — dynamic
  section renderer. Imports a static `sections` map of
  `{slug: {title, markdown}}` where markdown is `import … from
  '$lib/guide/<slug>.md?raw'`. Renders via `marked` passed through
  DOMPurify before `{@html}`.

`?raw` import is SvelteKit-native (Vite feature); no new build step.

## Content

Nine markdown files under `frontend/src/lib/guide/`:

| File | Content |
|---|---|
| `getting-started.md` | Welcome + read-only notice + sign-in pointer (ties to ADR-123). |
| `dashboard.md` | Counts, scoped filter header, search bar, recent-visits, knowledge graph embed. |
| `collections-sets.md` | Collection vs set concepts, navigation patterns. |
| `packages-diagrams.md` | Package hierarchy, diagram types, canvas basics. |
| `knowledge-graph.md` | Hierarchy flow, spread/label sliders, hover focus. |
| `search.md` | Global vs scoped search, result types, Add to AI context. |
| `ask-ai.md` | Context tab vs Chat tab, set scoping, session file upload, rate limits. |
| `bookmarks.md` | Bookmarking elements/diagrams, managing the list. |
| `admin.md` | Admin-only screens (Users, Audit, Locks, Settings) — visible but access-gated. |

Each page is ~300–500 words with 1–3 screenshots inline
(`![caption](/guide/<name>.png)`).

## Rendering

```svelte
<script lang="ts">
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';
  import { page } from '$app/state';
  import { SECTIONS } from '$lib/guide';

  let slug = $derived(page.params.section);
  let section = $derived(SECTIONS[slug] ?? SECTIONS['getting-started']);
  let html = $derived(DOMPurify.sanitize(marked.parse(section.markdown) as string));
</script>

<article>
  <h1>{section.title}</h1>
  {@html html}
</article>
```

`DOMPurify.sanitize` is mandatory per protocol #7; the test
`frontend/tests/unit/guide-sanitisation.test.ts` verifies that a
markdown fragment containing `<script>` is stripped.

## Nav bar

Left-hand column in `/guide/+layout.svelte` lists all 9 sections.
Active section is highlighted by comparing `page.params.section` to
the loop item's slug. Mobile (< 768 px) collapses the nav into a
select-like dropdown.

## Main app nav integration

`AppShell.svelte` adds a "Guide" entry at the top of the `navItems`
array. Visible in both the authenticated and anonymous shell variants
(SPEC-123-A). Icon: a book glyph matching the existing Lucide-style
inline SVGs.

## Screenshot generator

`frontend/tests/screenshots/generate.spec.ts` walks the app as an
admin user (full data visible) and writes viewport PNGs:

```ts
const SHOTS = [
  { name: 'dashboard', url: '/' },
  { name: 'collections', url: '/collections' },
  { name: 'sets', url: '/sets' },
  { name: 'packages', url: '/packages' },
  { name: 'diagrams', url: '/diagrams' },
  { name: 'knowledge-graph', url: '/?collection_id=…' },  // seeded fixture
  { name: 'search', url: '/?q=example' },                  // performs a search
  { name: 'ask-ai', url: '/ask' },
  { name: 'bookmarks', url: '/bookmarks' },
  { name: 'admin-users', url: '/admin/users' },
];
for (const s of SHOTS) {
  await page.goto(s.url);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: `static/guide/${s.name}.png`, fullPage: false });
}
```

Playwright config adds a new project `screenshots`, excluded from the
default `test:e2e` run. Invoked via `npm run screenshots`.

Screenshots are committed. CI does not run the generator (it needs a
seeded admin account + the full UAT fixture); developers regenerate
on meaningful UI change.

## Acceptance criteria

- Visiting `/guide` unauthenticated renders the getting-started page
  (SPEC-123-A permits this).
- Each section renders Markdown through DOMPurify — smoke test
  verifies no `<script>` survives sanitisation.
- Nav bar link clicks navigate without a full page reload (SvelteKit
  client-side navigation).
- `npm run screenshots` produces all 10 PNGs under
  `frontend/static/guide/` (some sections share images — dashboard
  + knowledge graph for example).
- `AppShell.svelte` shows a "Guide" nav item for both anonymous and
  authenticated users.

## Out of scope

- Auto-generating guide prose from BDD feature files (ADR-122
  rejected alternative).
- Versioning the guide per-release. Guide changes ship alongside
  features in the same commit.
- Localisation (English only for v4.1).
