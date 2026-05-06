# ADR-146: Extension Source Tracking and Upgrade Workflow

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-146 |
| **Initiative** | Extension manager — source tracking, upgrade flow, daily scanner |
| **Proposed By** | Engineering |
| **Date** | 2026-05-06 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris extensions (mnemos, scenia, docref) — which
each ship from a different source (a sibling Git clone, an npm
dependency pinned to a GitHub branch, or a backend-native module) and
have their own release cadence —

**facing** the problem that the extension manager UI hardcoded a
`KNOWN_EXTENSIONS` array with a static version string and gave the
operator no way to see whether each extension was up to date or where
the upstream source lived,

**we decided to** make extensions data-with-source rather than
config-file constants:
- Add `source_method` (`local` / `github` / `npm`),
  `source_url`, `latest_version`, `latest_version_checked_at`
  columns to the `extensions` table.
- Maintain a single shared registry at `extensions/sources.json`
  consumed by the backend (`backend/app/extensions/sources.py`), the
  frontend (via the `/api/extensions` response), and the daily
  scanner workflow (`scripts/check_extension_updates.py`).
- Add `POST /api/extensions/{id}/check-update` (queries GitHub
  releases, persists `latest_version`) and `POST
  /api/extensions/{id}/upgrade` (mnemos: stops container, pulls
  latest from `source_url`, restarts).
- Surface source method, source URL, installed/latest version, and
  an "Update available" pill in the extension manager UI.
- Add a daily GitHub Action that diffs each github-sourced extension
  against `extensions/manifest.json` and opens a single deduplicated
  issue per outdated extension.

**to achieve** transparent, scannable, low-touch extension upgrade
hygiene — operators see at a glance which extensions need attention,
and the daily scanner files an issue without anyone having to remember
to check.

**accepting** that:
- A second source-of-truth (`extensions/manifest.json`) duplicates
  the version field already in the `extensions` row. We accept this
  because the manifest is what the daily scanner compares against
  *without* hitting any database — it's the "what's currently
  shipped" baseline, bumped in upgrade PRs.
- The "currently shipped" version is now committed in the repo
  rather than derived. Bumps land alongside the upgrade PR; this
  keeps the workflow simple and audit-friendly.
- The scanner only files one issue per extension at a time; if mnemos
  has v2 → v3 → v4 in rapid succession, the dedup means the operator
  sees a single rolling issue.

## Reference

| Document | Purpose | Type | Link |
|----------|---------|------|------|
| SPEC-146-A | Extension source tracking schema, endpoints, scanner workflow | Technical Specification | [specs/SPEC-146-A-Extension-Source-Tracking.md](./specs/SPEC-146-A-Extension-Source-Tracking.md) |
| ADR-111 | MNEMOS Semantic Retrieval (v5.5.0 amendment for auto-clone) | Decision Record | [ADR-111-MNEMOS-Semantic-Retrieval.md](./ADR-111-MNEMOS-Semantic-Retrieval.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-05-06 |
| Approved | Engineering | 2026-05-06 |
