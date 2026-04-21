# Canvas Editing

> **Sign in to use this.** Canvas editing is available to users with the **architect** or **admin** role. Signed-out visitors can view every diagram but not modify them.

Iris diagrams are interactive canvases — every element, relationship, and label is an object you can add, move, rename, re-type, or delete. This section covers the full editing surface.

## Edit mode

Every diagram page opens in **browse mode** by default. Click **Edit Canvas** in the toolbar (or press `Enter` when focus is on the diagram) to switch to edit mode. The toolbar gains add / link / connect / delete actions and a red "unsaved changes" indicator appears once you make any modification.

Toggle back to browse mode at any time with **Done Editing**. If you have unsaved changes Iris shows an "Unsaved changes — save or discard?" dialog.

## Locks

Only one user edits a diagram at a time. When you enter edit mode Iris acquires a **15-minute lock** (auto-extended while you're actively editing). If another user is already editing, you'll see:

> ⚠ *This diagram is being edited by `@username`. Try again later.*

If someone disconnects without saving, admins can force-release the lock from **Admin → Locks**. Locks auto-release on save, on **Done Editing**, and on page close.

## Add an element

Three ways to add an element to the canvas:

1. **Toolbar → Add Element.** Opens a dialog with element-type picker, name, and optional description. Useful when you want a brand-new element.
2. **Toolbar → Link Element.** Opens a searchable picker of existing elements in the current set. The element gets added to the canvas as a reference; changing it here updates it everywhere.
3. **`Ctrl + N` (or `Cmd + N` on macOS).** Keyboard shortcut for Add Element.

Each element appears at the centre of the visible canvas area. Drag to reposition.

## Connect two elements

Two ways to draw a relationship:

1. **Keyboard.** Select an element (click or `Tab`). Press `C` to enter connect mode — the element gains a blue highlight. `Tab` to the target element and press `Enter` to create the link.
2. **Toolbar → Link Element.** When two elements are already selected Iris offers a relationship type dropdown (e.g. `causal_link` for DoView, `association` for UML, `flow` for ArchiMate Business).

Cancel connect mode with `Escape`.

## Move, resize, delete

- **Arrow keys** — move the selected element by 10 px per press. Hold `Shift` for 50 px steps.
- **Resize handles** — four corner + four edge handles appear when an element is selected. Drag any to resize. Elements with a square aspect ratio snap automatically.
- **`Delete`** — remove the selected element or relationship. A confirmation prompt appears if the element is referenced elsewhere.

## Undo / redo

- `Ctrl + Z` (undo) — supported for every canvas operation: add, move, resize, delete, connect, disconnect, reconnect.
- `Ctrl + Y` or `Ctrl + Shift + Z` (redo).

History is in-memory per edit session. Switching to browse mode without saving discards the history (but also the changes). Closing the tab discards everything too — **save often**.

## Saving

Click **Save** in the toolbar (disabled until there are unsaved changes). Save writes a new version of the diagram to the server — every save creates a version-history entry, and the old version is recoverable from the **Version** section (see [Imports & Data](imports-data) for rollback).

There is **no autosave** — this is a deliberate choice to avoid surprising overwrites. The editor keeps a local undo history between saves, so accidental deletes are recoverable until you click Save.

## Fullscreen / focus view

Click the **Maximise** icon (top-right of the canvas area) or press `F` to enter **Focus View** — the left sidebar and header hide, and the canvas expands to fill the browser. Press `Escape` or the **Exit** button (top-left) to return.

Focus view is especially useful on laptop screens when working with large DoView or ArchiMate diagrams.

## Search within a diagram

The sidebar's tree view shows every element and sub-diagram in the current package hierarchy. A search box at the top filters the tree by name, letting you jump to a specific element across a large model. The canvas view itself has no separate search field — use the tree.

## Next steps

- [Notations](notations) — reference for the diagram types Iris supports (Simple, UML, ArchiMate, C4, Sequence, DoView, Roadmap).
- [Comments](comments) — leave feedback and discuss changes with your team.
- [Imports & Data](imports-data) — rollback to a previous version, restore a deleted diagram, or import models from Sparx EA / PowerPoint.
