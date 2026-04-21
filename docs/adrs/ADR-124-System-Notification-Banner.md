# ADR-124: System Notification Banner

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-124 |
| **Initiative** | Operations |
| **Proposed By** | Engineering |
| **Date** | 2026-04-21 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris shipping v4.1.0 with anonymous read-only
access (ADR-123) and an AI assistant whose upstream providers can be
temporarily unavailable (the immediate trigger — the
`api.agentics.org.nz` provider returned 502 Bad Gateway from its edge,
causing every AI call on UAT to fail), leaving admins with no way to
communicate system status to the many readers who can now visit the app
without an account,

**facing** the need for a lightweight admin-posted top-of-screen banner
("AI provider being worked on — temporarily unavailable", "Scheduled
maintenance 19:00 UTC", etc.) visible to every visitor including
anonymous ones, editable by admins in-app without a deploy, cleared by
editing to empty,

**we decided for** **a single free-text setting** stored in the existing
`settings` key-value table under key `notification_banner_message`,
exposed via a new **public** `GET /api/notifications/banner` endpoint
(returns `{"message": "..."}`) so anonymous users can see it, and edited
via the existing admin-gated `PUT /api/settings/notification_banner_message`
(no new write endpoint — DRY). Frontend mounts a `SystemBanner.svelte`
component inside `AppShell` that polls the public endpoint every 60 s and
renders a sticky top strip when the message is non-empty, with a Dismiss
button that hides the banner per-browser-session via localStorage,

**and neglected** (a) a dedicated `notifications` table with multiple
banners, severities, and expiry dates — over-engineered for the stated
need; revisit if a second banner type ever appears; (b) a realtime
push (WebSocket/SSE) instead of polling — adds infrastructure for a
message that changes rarely, 60 s polling is cheap and invisible to
users; (c) rendering the banner as Markdown — encourages admins to
paste HTML and bypass Svelte's escape-by-default; plain text is
sufficient for the "service status" messages this is built for; (d)
forcing a new settings subsystem when the generic `settings` table
already has migrations, router, admin UI, and audit — DRY with the
existing pattern.

**to achieve** a minimal operational tool for communicating with every
Iris user, reusing the existing settings infrastructure end-to-end, with
one new file (the banner component) and one new public endpoint,

**accepting that** a single admin-posted banner cannot differentiate
severity or target specific user groups (the stated need is a single
system-wide message; any future need for per-role or typed alerts
justifies its own ADR), that polling every 60 s means up to 60 s of
staleness between admin edit and visible update (acceptable for a
status message), that dismissal is per-browser-session so the same
admin-posted message re-appears after a browser restart (acceptable —
the banner is the communication channel, and admins clear it when
they want it to stop showing), and that the banner renders as plain
text so admins cannot include links, bold, or emoji (protocol #7 bans
unsanitised `{@html}`; a plain-text policy is the simplest safe
default).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| System Notification Banner | New settings key `notification_banner_message`. New public endpoint `GET /api/notifications/banner` (returns `{message}`). Existing admin-gated `PUT /api/settings/{key}` edits it. `SystemBanner.svelte` mounts in `AppShell`, polls every 60 s, renders a sticky top strip when message is non-empty, Dismiss button stores a per-session `iris-banner-dismissed-<hash>` flag in localStorage so the same message doesn't re-pop after dismiss. Edit UI added to `/admin/settings` (textarea). | [SPEC-124-A](./specs/SPEC-124-A-System-Notification-Banner.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-123 | Anonymous Read-Only Bypass | Public banner endpoint so anonymous visitors see the message. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-124-A | System Notification Banner | Technical Specification | [specs/SPEC-124-A-System-Notification-Banner.md](./specs/SPEC-124-A-System-Notification-Banner.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-21 |
| Approved | Engineering | 2026-04-21 |
