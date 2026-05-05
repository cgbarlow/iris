# Packages & Diagrams

**Packages** are nested containers within a set. **Diagrams** are the canvas-based artefacts that live inside packages. Most of the modelling work in Iris happens at these two layers.

## Packages

A set can have many top-level packages, and each package can contain:

- Sub-packages (arbitrary depth).
- Diagrams.
- Relationships to other packages (e.g. "depends on").

Typical use: a set for an organisation contains a package per business capability, each package containing the diagrams that model that capability.

![Packages](/guide/packages.png)

### Hierarchy navigation

Each package detail page has three sections:

- **Tree.** The package's full descendant hierarchy (sub-packages and diagrams), laid out as a collapsible tree. Click any node to open it. A search box filters the tree by name — useful in large trees.
- **Relationships.** Package-to-package links with their type (depends-on, contains-reference, etc.).
- **Details.** Description, tags, version history, comments.

### Creating, editing, reordering

> **Sign in as architect or admin.**

- **New Package** — button on the set detail page. Name, optional description, optional parent (to create nested).
- **Rename** — edit from the package detail page. Renames are versioned; the old name stays in version history.
- **Move (change parent)** — edit the **Parent package** field. The move is validated server-side to prevent cycles (you can't make a package its own ancestor).
- **Reorder within a parent** — drag-reorder from the tree view. `sequence_order` persists per package.
- **Delete** — soft-delete, recycle-bin recoverable.

### Templates and cloning

> **Sign in as architect or admin.**

- Mark a package as a **template** (checkbox in Edit). Templates appear in the "Clone from template" picker when creating new packages, copying their structure without their data.
- **Clone** a package outright — copies sub-packages, diagrams, and elements into a new subtree under the target parent.

## Diagrams

A diagram is a visual model — a DoView strategy diagram, a process flow, a UML class diagram, an ArchiMate enterprise view, a C4 context diagram, a sequence diagram, or a Roadmap.

![Diagrams](/guide/diagrams.png)

### Creating and editing

> **Sign in as architect or admin.**

- **New View** — from the package detail page or `/views` (the **+ New** dropdown). Choose a notation from the picker; each notation has its own toolbar (see [Notations](notations)). Pick **Markdown** to create a Text view.
- **Edit canvas** — see [Canvas Editing](canvas-editing) for the full edit-mode surface (add element, connect, move, undo/redo, save, locks, fullscreen).

### Diagram types

Iris supports seven notations: **Simple**, **Component**, **UML**, **ArchiMate**, **C4**, **Sequence**, **DoView**, and **Roadmap** (via Scenia). Each has its own element types, relationship types, and palette. See [Notations](notations).

### Export

> **Sign in.**

From any diagram page, use the **Export** menu (toolbar): SVG (vector, theme-aware) or PNG (raster, fixed-size, larger file). SVGs include embedded text; PNGs are handy for presentations.

### Tags

> **Sign in.**

Diagrams and elements support **tags** — free-text labels used for filtering and grouping. Add tags from the diagram detail page's tag field; autocomplete suggests existing tags in the current set. Tags don't carry semantic meaning — they're purely user-defined.

## Cross-diagram navigation

Elements on one diagram can reference elements or sub-diagrams. A classic C4 use case: a Container diagram's "API" box links to a Component-level diagram that decomposes it. Iris renders these as dashed edges on the parent diagram; clicking the label opens the linked diagram.

Creating cross-references is automatic when you drag an element from one diagram's tree-view onto another diagram's canvas.

## Next steps

- [Canvas Editing](canvas-editing) — the full edit-mode toolbar.
- [Notations](notations) — notation-specific element types and relationships.
- [Knowledge Graph](knowledge-graph) — see all your packages and diagrams at once.
