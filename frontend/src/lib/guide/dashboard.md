# Dashboard

The dashboard is Iris's landing page. It shows counts for the current scope, an embedded knowledge graph, a global search bar, and (when signed in) your recent-visits and bookmarks.

![Dashboard](/guide/dashboard.png)

## Discover vs History tabs

Two tabs at the top:

- **Discover** (default) — counts, graph, search, bookmarks.
- **History** — a chronological list of entities you've viewed, grouped as *Today*, *Yesterday*, *This week*, and by month. Anonymous users see no history (no login = no identity to track against).

## Counts panel

Five tiles across the top show how many collections, sets, packages, diagrams, and elements exist in the **current scope**. If you've previously viewed a specific set or collection, the scope is remembered across tabs in that browser session, and the counts reflect it. The active scope name appears in the header so you know what you're filtered to; click **Iris** in the top-left to clear it.

## Knowledge graph

Directly below the counts, Iris embeds an interactive force-directed graph of the current scope. Every entity is a node; every relationship is an edge. Nodes are colour-coded by type:

- 🔴 Collections
- 🟣 Sets
- 🟠 Packages
- 🟢 Diagrams

The graph has its own settings panel (top-right of the graph area) for spread, label density, size contrast, and link length — see [Knowledge Graph](knowledge-graph).

**Click any node** to jump to its detail page. **Hover** for 400 ms to trigger focus-fade: unrelated nodes dim so you can follow relationships at a glance.

## Search

The search bar sits beneath the graph. Unlike the counts panel, **the search bar is always global** — typing on `/` with no URL parameters searches every collection and every set. A remembered scope does not silently filter search (fixed in v4.1.3; see ADR-121).

Results appear inline with type badges; each result has a deep-link to the entity detail page plus an **Add to AI context** button — see [Search](search) and [Ask AI](ask-ai).

## Recent visits

> **Signed in only.**

Below search, a grouped list of entities you've visited recently (today / yesterday / this week / earlier). Click any entry to jump back.

## Bookmarks

> **Signed in only.**

A summary of your bookmarked diagrams, packages, and elements sits above Recent Visits. Click **Manage bookmarks** to go to the full page — see [Bookmarks](bookmarks).

## Next steps

- [Collections & Sets](collections-sets) — the organising layer above sets.
- [Search](search) — how the global search bar actually works under the hood.
- [Knowledge Graph](knowledge-graph) — make the graph a productive view, not just a picture.
