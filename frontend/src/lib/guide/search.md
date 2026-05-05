# Search

Iris indexes every entity name and description for full-text search. The dashboard search bar and list-page search boxes both call the same index; under the hood, SQLite deployments use FTS5 and Postgres/Supabase deployments use `tsvector`.

![Search](/guide/search.png)

## Global vs scoped

- **Dashboard search bar** is **always global.** Typing on `/` with no URL parameters returns results from every set and every collection. A remembered scope (for counts) does not silently filter search — see ADR-121.
- **List-page search boxes** (Collections, Sets, Diagrams, Elements) are scoped to that list. They don't filter by the dashboard's remembered scope; each list page has its own type-specific index.
- **Deep-linked scoped search** — add `?set_id=<id>` or `?collection_id=<id>` to the dashboard URL and the search bar on that page scopes to it. Useful for URL-sharing narrow results.

## What results look like

Each hit includes:

- **Type badge** (Collection / Set / Package / Diagram / Element).
- **Name** (the primary match target).
- **Description excerpt** (if any).
- **Parent scope** (set name, collection name, package name where relevant).
- **Rank indicator** (higher = better match on the tsvector / FTS5 ranking).

Click a result to open the entity detail page. The scope automatically updates to reflect the clicked entity.

## Query syntax

Simple, prefix-matching:

- `msd` matches "msd", "MSD", "NZ Ministry of Social Development (MSD) ...".
- `nz government` matches entities with both "nz" and "government" in name or description.
- No boolean operators, no exact-phrase quoting — keep it simple.

## Indexing

Whenever an entity is created, updated, or deleted, its search index entry is updated in-line (the entry is written in the same transaction as the entity's version row — see ADR-125). No manual re-index needed. If the search index ever gets out of sync, admins can force a full rebuild from **Admin → Settings → Rebuild Search Index** (available only in SQLite mode; Postgres has trigger-driven indices that don't need manual rebuild).

## Add to AI context

Every search result has an **Add to AI context** button. Clicking it stages that entity for your next Ask AI question — the AI will treat that entity's content as primary context. See [Ask AI](ask-ai) for how the context tray works.

## Searching on specific pages

- `/collections` — filter the collection list by name.
- `/sets` — filter sets; includes the parent collection name as search text.
- `/views` — filter views (diagrams + text) by name, description, or type.
- `/elements` — filter elements by name, element type, or tag.
- `/packages/[id]` — search **within** a package's tree (elements and sub-views).
- `/views/[id]` — search within the view's side-tree.

## Tips

- **Use less text, not more.** FTS5 and tsvector both rank by term density — "msd" returns better results than "find msd please".
- **Scope via URL** when you want to share a scoped search. Copy the URL after scoping and the recipient gets the same filtered view.
- **Add to AI context** lets you pre-load the AI with a specific entity rather than pasting its description.

## Next steps

- [Ask AI](ask-ai) — how search results feed the AI assistant.
- [Dashboard](dashboard) — the global search surface.
- [Knowledge Graph](knowledge-graph) — when visual exploration beats text search.
