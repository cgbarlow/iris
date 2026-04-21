# Getting Started

Welcome to **Iris** — the Integrated Repository for Information & Systems.

Iris is a knowledge-graph-backed architecture tool. It stores **collections** of organisations, their **sets** of data, the **packages** that organise that data, the **diagrams** within them, and every **element** on every diagram — plus the relationships that connect them. You can browse, search, visualise, edit, comment, version-control, and ask an AI assistant questions across all of it.

![Iris dashboard](/guide/dashboard.png)

## Read-only by default

You're viewing Iris in **read-only mode**. Without signing in you can:

- Browse every collection, set, package, diagram, and element.
- Run searches across the whole knowledge graph.
- Explore the knowledge graph visualisation with full interactivity.
- Ask the AI assistant questions (rate-limited to 10 requests per hour per IP).
- Read comments and version histories.

To **create, edit, import, delete, or administer** anything, click **Sign in** in the top-right corner.

## The hierarchy

Iris organises content in five layers:

1. **Collections** — top-level groupings (e.g. "DoView Strategy Models").
2. **Sets** — a member of a collection (e.g. "NZ Government", "Large Company").
3. **Packages** — nested containers within a set, typically a project or domain area.
4. **Diagrams** — individual diagrams within a package, in one of seven notations.
5. **Elements** — shapes and relationships on each diagram.

Every level carries its own metadata, versioning, thumbnails, tags, comments, and bookmark support.

## Roles at a glance

| Role | Can read | Can edit | Can admin |
|---|---|---|---|
| **Anonymous** | ✔ everything read-only | ✘ | ✘ |
| **Viewer** | ✔ | ✘ | ✘ |
| **Reviewer** | ✔ | ✔ comments only | ✘ |
| **Architect** | ✔ | ✔ everything except admin | ✘ |
| **Admin** | ✔ | ✔ | ✔ users, extensions, banner, providers |

See [Admin & Permissions](admin) for the full permissions matrix.

## Where to go next

- [Dashboard](dashboard) — start here to get a feel for what's in this Iris instance.
- [Knowledge Graph](knowledge-graph) — the interactive force-directed visualisation.
- [Canvas Editing](canvas-editing) — learn to draw, connect, and edit diagrams (sign-in required).
- [Ask AI](ask-ai) — chat with the AI about your architecture.
- [Keyboard Shortcuts](keyboard-shortcuts) — full reference.
