# Dashboard

The dashboard is the landing page — it shows counts, a search bar, a recent-visits panel, and the knowledge graph.

![Dashboard](/guide/dashboard.png)

## Counts panel

At the top, Iris shows how many collections, sets, packages, diagrams, and elements exist in the current scope. If you've previously viewed a specific set or collection, that scope is remembered and the counts reflect it — the active scope name appears in the header so you know what you're filtered to.

## Search

The search bar runs a full-text search across all content you can see. **Search ignores the remembered set/collection scope** — type anything and you see global results. To run a scoped search, pass `?set_id=<id>` or `?collection_id=<id>` in the URL (this happens automatically when you click into a scope from elsewhere).

## Knowledge graph

The embedded knowledge graph visualises the current scope. Each node is an entity; edges are the relationships. See the **Knowledge Graph** section of this guide for details on layout, spread, and hover-focus.

## Recent visits

Below the graph, a grouped list shows what you've looked at today, yesterday, this week, and earlier. Click any entry to jump back into it.
