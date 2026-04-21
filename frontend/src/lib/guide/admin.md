# Admin & Permissions

> **Sign in as admin to use this.** Admin routes are gated in the frontend (redirect to `/login`) *and* in the backend (401 on every admin API call from a non-admin token).

This section describes every admin-only surface in Iris.

![Admin](/guide/admin.png)

## Roles and permissions

Iris ships with four seeded roles:

| Role | Read | Create / edit | Delete | Import | Admin |
|---|---|---|---|---|---|
| **Admin** | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Architect** | ✔ | ✔ | ✔ (soft-delete) | ✔ | ✘ |
| **Reviewer** | ✔ | comments only | ✘ | ✘ | ✘ |
| **Viewer** | ✔ | ✘ | ✘ | ✘ | ✘ |

Plus **anonymous** — no role, read-only to everything that isn't under `/admin/*`.

Permissions are stored in a `role_permissions` table and enforced server-side on every API call via FastAPI dependencies. Non-admin users who craft direct URLs to admin endpoints get HTTP 403.

## Users

**Admin → Users.**

- **Create user** — username, initial password, role.
- **Edit user** — change role, deactivate / reactivate.
- **Delete user** — soft-delete (user can be restored from the recycle bin within the retention window).

Passwords are hashed with argon2 server-side.

## Audit log

**Admin → Audit.**

Every write to Iris (create, update, delete, move, import, rollback) is appended to an **immutable hash-chained audit log**. Each entry contains: timestamp, user id, endpoint, a hash of the request body, and the hash of the previous entry — tampering is detectable.

Filter by date range, user, or action. Export to CSV for compliance reviews.

## Locks

**Admin → Locks.**

Shows every active edit lock in the system. Columns: entity type, entity id, locked-by user, lock-acquired timestamp, last heartbeat.

- **Force release** — use this when a user has disconnected without releasing (e.g. browser crashed). Releasing is audit-logged with "forced" flag.

## Settings

**Admin → Settings.**

- **Session timeout** — minutes before an idle session expires (default 15).
- **Gallery thumbnail mode** — SVG (inline, smaller) or PNG (server-rendered).
- **Debug AI logging** — verbose prompts / streaming in server logs. Useful when triaging Ask AI issues.
- **System notification banner** — plain text banner shown to every visitor. See [System Notification Banner](#system-notification-banner) below.
- **Rebuild search index** — SQLite-mode only. Triggers a full FTS5 rebuild. Postgres uses triggers and needs no manual rebuild.
- **Seed example data** — populates the Default set with representative diagrams across every notation. Safe to run multiple times.
- **Regenerate thumbnails** — re-renders PNG thumbnails for every diagram (needed if you change the theme palette or graph physics defaults).

## AI providers

**Admin → AI Providers.**

- **Add provider** — pick a provider type (Anthropic / OpenAI / Ollama / LM Studio / OpenRouter / custom), paste API key, select default model, give it a name.
- **Test** — run a one-shot "say 'ok'" against the provider. Friendly error messages on failure (see v4.1.1 error mapper).
- **Ping** — continuous background health check. Results feed the green/red dot next to each provider in the chat picker.
- **Edit / delete**.
- **Set default** — one provider marked default; new conversations use it unless the user picks another.
- **Advanced settings per provider** — top_p, top_k, min_p, frequency_penalty, presence_penalty, stop sequences.

### Creation prompts

**Admin → AI Providers → Creation Prompts.**

Edit the system prompts used for AI-generated content. Three tiers:

- **Base system prompt** — always-on, establishes Iris's persona.
- **Notation-specific prompt** — e.g. "when generating DoView, use only causal_link relationships".
- **Diagram-type prompt** — specific to a sub-variant (e.g. "DoView Strategy Diagram").

Changes apply on the next AI request.

## Extensions

**Admin → Extensions.**

- **Scenia** — roadmapping app. Install (runs schema migrations), enable, disable. See [Roadmap (Scenia)](roadmap-scenia).
- **MNEMOS** — semantic retrieval for Ask AI. Install, enable, disable. See [Ask AI](ask-ai).
- **DocRef** — legislation import from legislation.docref.nz. Install, enable, disable.

Extensions are opt-in; none ship enabled by default.

## Themes

**Admin → Settings → Themes.**

Create and edit visual themes for the canvas:

- **Element colours** per element type (background, border, text).
- **Font overrides**.
- **Edge styling** (stroke width, dash pattern).

Themes are notation-scoped — a DoView theme affects only DoView diagrams.

## Graph settings admin defaults

**Admin → Settings → Knowledge Graph Defaults.**

For each of Spread / Labels / Contrast / Link Length, set a **default value** at the admin level. Defaults cascade:

```
global → collection-specific → set-specific
```

User-local `localStorage` overrides always win over admin defaults.

## System notification banner

**Admin → Settings → System Notification Banner.**

Paste a plain-text message. It renders as a sticky yellow strip at the top of every page for every visitor (anonymous included) within 60 seconds. Empty to clear.

Useful for:

- "AI provider being worked on — temporarily unavailable"
- "Scheduled maintenance 19:00 UTC"
- "New feature: knowledge graph spread slider now admin-configurable"

Users can dismiss the banner per message per browser session. A different message re-shows even after dismissal (hash-keyed).

## Thumbnail regeneration

**Admin → Settings → Regenerate Thumbnails.**

Re-renders PNG thumbnails for every diagram. Needed after:

- Changing theme palette defaults.
- Upgrading the thumbnail-generation library (cairosvg).
- Importing a large batch of diagrams (their thumbnails generate lazily, but a bulk regen is faster).

## Example data seeding

**Admin → Settings → Seed Example Diagrams.**

Populates the Default set with diagrams across every notation (Simple, Component, UML, ArchiMate, Sequence, C4, DoView). Safe to run multiple times — existing diagrams aren't duplicated. Useful on a fresh install or a demo environment.

## Next steps

- [Imports & Data](imports-data) — recycle bin, versioning, imports.
- [Ask AI](ask-ai) — provider setup, creation prompts, MNEMOS.
- [Themes & Accessibility](themes-accessibility) — theme management.
