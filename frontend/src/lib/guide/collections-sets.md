# Collections & Sets

**Collections** group related **sets**. Sets are the primary unit of data — an organisation, a project, a domain, a product line.

## Collections

A collection is a container for one or more sets. It has a name, a description, a thumbnail, and timestamps. Typical examples: *DoView Strategy Models* (a portfolio of strategy diagrams across multiple organisations), *Sparx EA Imports* (a container for imported models from Enterprise Architect), *Scenia Roadmaps* (roadmap sets across teams).

### Browsing

Visit `/collections` to see every collection with its set count, package count, diagram count, and element count. Click a collection card to **scope the whole app to it** — the sidebar, search, counts, and knowledge graph all filter to the chosen collection until you clear the scope.

![Collections](/guide/collections.png)

### Creating, editing, deleting

> **Sign in as architect or admin.**

- **New Collection** button (top-right of `/collections`) opens a dialog with name and description fields.
- **Edit** — click the pencil icon on a card, or open the collection detail page and click **Edit**. Name, description, and thumbnail are editable.
- **Delete** — soft-deletes the collection; the recycle bin lets you restore it within the retention window. Deleting a collection unlinks its sets (they become collection-less but remain). Sets don't cascade-delete unless you force-delete with the `force=true` option.

### Thumbnails

Each collection can have a thumbnail — choose between:

- **Auto-generated SVG** from the contents (default).
- **PNG** server-rendered (requires the thumbnail regeneration admin task).
- **Custom image** uploaded by an admin (≤ 2 MB, PNG or JPEG).

Thumbnails appear on the collections list, on the dashboard counts, and in the set-picker when moving content between collections.

## Sets

Sets live inside (or alongside) collections. A set has a name, description, a collection reference (optional), and all the content: packages, diagrams, elements.

![Sets](/guide/sets.png)

### The Default set

Every Iris instance has a built-in **Default** set. You can't delete it; it holds anything that was created without being assigned to a specific set. Useful for quick prototypes or ad-hoc imports.

### Browsing

`/sets` shows a flat list of every set across every collection. Each card shows:

- Set name and description.
- The parent collection (or "(no collection)" if none).
- Element count and diagram count badges.

Click a set to scope the app to it.

### Moving between collections

> **Sign in as architect or admin.**

On any set detail page, **Edit** → change the **Collection** dropdown → Save. The set's content travels with it; nothing moves in the file system, only the link.

### Batch actions

> **Sign in as architect or admin.**

Checkboxes on the `/sets` list let you select multiple sets and:

- **Move to collection** — reassign the selected sets to a different collection in one action.
- **Delete** — soft-delete the selected sets (recycle bin recoverable).

## Scoping behaviour

When you scope the app to a collection or set, that choice is **remembered in sessionStorage** so it survives navigation within the browser tab. It does **not** survive a tab close. To clear scope:

- Click the **Iris** logo in the top-left header.
- Or visit `/` without any URL parameters.
- Or pick a different collection / set.

The search bar is a deliberate exception to scope: it always runs globally on `/`.

## Next steps

- [Packages & Diagrams](packages-diagrams) — what lives inside a set.
- [Dashboard](dashboard) — the scope-aware landing page.
- [Knowledge Graph](knowledge-graph) — visualise a set's contents in 2D.
