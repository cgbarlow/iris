# Roadmap (Scenia)

Iris integrates [Scenia](https://github.com/cgbarlow/waylonkenning_scenia), an open-source roadmapping tool, as an optional extension. When enabled, Iris gains a first-class roadmap data type and two access points.

## What Scenia offers

Scenia organises time-phased delivery around eight entity types:

- **Strategies** — long-horizon goals ("modernise customer onboarding").
- **Programmes** — bundles of work delivering a strategy.
- **Initiatives** — concrete, bounded projects under a programme.
- **Assets** — physical or informational resources an initiative produces.
- **Applications** — software the initiative relies on or changes.
- **Milestones** — dated checkpoints.
- **Resources** — people and budget.
- **Dependencies** — explicit links between the above.

A Scenia roadmap is a *timeline* view: horizontal lanes per strategy or programme, months / quarters on the x-axis, initiatives laid out as bars with milestones dotted on top.

## Two access points

- **`/roadmap`** — Iris-native tabular view. Every Scenia entity shows as a row; click any row to open the linked entity in the full Scenia UI. Set selector at the top filters the data.
- **`/scenia`** — the full Scenia React app, embedded inside Iris. Identical to Scenia when used stand-alone, but the backing data is stored in Iris (not Scenia's own IndexedDB), so Scenia data follows the same permissions / roles / versioning / audit log as every other Iris entity.

## Enabling the extension

> **Admin task.** Non-admins cannot install or enable extensions.

1. **Admin → Extensions** in the sidebar.
2. Find **Scenia** in the list.
3. Click **Install** (runs the Scenia schema migration idempotently), then **Enable**.

Once enabled, the **Roadmap** nav item appears in the sidebar for every signed-in user, and the `/scenia` route becomes accessible.

## Data sync

Scenia and the Iris roadmap view share the same data store: the `strategies`, `programmes`, `initiatives`, `assets`, `applications`, `milestones`, `resources`, and `dependencies` tables live in the Iris database. Edits in Scenia appear in `/roadmap` immediately (and vice versa). No external sync daemon; no eventual consistency window.

## Scope scoping

Scenia data is **set-scoped** — each set has its own roadmap. Switch sets from the Iris header to load a different set's roadmap data in Scenia. Moving a roadmap from one set to another requires admin intervention.

## Exporting from Scenia

Scenia supports its own export format (JSON backup / restore, plus PDF timeline export). These work end-to-end against the Iris-backed data store.

## Next steps

- [Admin & Permissions](admin) — enabling and disabling the Scenia extension.
- [Collections & Sets](collections-sets) — how set scoping shapes what Scenia shows.
