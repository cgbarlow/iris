# SPEC-146-A: Extension Source Tracking and Upgrade Workflow

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-146-A |
| **Implements** | ADR-146 |
| **Date** | 2026-05-06 |
| **Status** | Implemented in v5.5.0 |

## Schema additions

SQLite (`backend/app/migrations/m046_extensions_source.py`) and
Postgres (`backend/app/migrations/supabase/m048_extensions_source.sql`)
add four columns to `extensions`:

| Column | Type | Default | Notes |
|---|---|---|---|
| `source_method` | TEXT | `'local'` | `local` / `github` / `npm` |
| `source_url` | TEXT | NULL | The canonical URL the extension was pulled from |
| `latest_version` | TEXT | NULL | Latest release tag known to Iris (set by check-update) |
| `latest_version_checked_at` | TEXT | NULL | ISO timestamp of the most recent check |

## Source registry

`extensions/sources.json` is the single source-of-truth. The backend
imports it via `backend/app/extensions/sources.py`; the daily action
script reads it directly. Format:

```json
{
  "extensions": {
    "<id>": {
      "name": "...",
      "description": "...",
      "source_method": "github" | "local" | "npm",
      "source_url": "...",
      "github_owner": "...",
      "github_repo": "...",
      "supports_auto_upgrade": true | false
    }
  }
}
```

`extensions/manifest.json` holds the "currently shipped" version per
extension, bumped in upgrade PRs:

```json
{ "versions": { "<id>": "1.0.0", ... } }
```

## API endpoints

### POST /api/extensions/{id}/check-update

Admin only. Looks up the extension's `github_owner`/`github_repo` from
the registry, queries `https://api.github.com/repos/.../releases/latest`,
persists `latest_version` + `latest_version_checked_at`, returns:

```json
{
  "id": "<id>",
  "installed_version": "1.0.0",
  "latest_version": "v2.0.0",
  "latest_version_checked_at": "2026-05-06T18:00:00Z",
  "update_available": true,
  "source_url": "https://github.com/<owner>/<repo>"
}
```

Returns 400 if the extension's source method isn't `github`. Returns
502 if the GitHub API call fails.

### POST /api/extensions/{id}/upgrade

Admin only. Currently supported for `mnemos` only (other extensions
return 501). For mnemos: stops the container, runs
`clone_or_update_repo(source_url)`, restarts the container, and
updates the row's `version` to the new `latest_version`.

## Daily scanner workflow

`.github/workflows/extensions-check.yml` runs at `7 8 * * *` (08:07
UTC). It runs `scripts/check_extension_updates.py`, which:

1. Reads `extensions/sources.json` and `extensions/manifest.json`.
2. For each `source_method == 'github'` extension, fetches
   `releases/latest` via the GitHub API.
3. Compares the latest tag to the manifest version using a
   permissive semver comparator (strips `v`-prefix and prerelease
   tails).
4. If newer, runs `gh issue list --search "Upgrade: <id> extension
   in:title"` — if no open issue matches, runs `gh issue create`
   with the canonical title and a body that links to the release.

The workflow uses the default `GITHUB_TOKEN` for both GitHub API calls
and `gh` CLI authentication. Manual trigger via `workflow_dispatch`.

## UI affordances

`frontend/src/routes/admin/settings/extensions/+page.svelte`:

- Renders a source-method badge (`GitHub` / `npm` / `Local`).
- Renders the `source_url` as a `target="_blank"` link.
- Renders installed-vs-latest as `vX → vY` when newer, `vX (latest
  vY)` when up-to-date.
- Shows an `Update available` pill when `isNewerSemver(latest,
  installed)` returns true.
- Shows a `Check for updates` button per row for github-sourced
  extensions.
- Shows an `Upgrade to vY` button when an update is available AND
  the extension's `supports_auto_upgrade` flag is true.

## Reuse / DRY

- `extensions/sources.json` is the only place GitHub coordinates
  live. Backend, frontend (via API), and the GH Action all read from
  it.
- `frontend/src/lib/utils/semverCompare.ts` and
  `scripts/check_extension_updates.py::is_newer` are independent
  implementations of the same numeric-prefix-only comparator. We
  accept the duplication because they live in different runtimes
  (TypeScript vs Python); both have parity tests pinning their
  contract.
- The router's `_compare_semver` is a third copy in Python — reused
  by the upgrade endpoint when comparing installed vs latest.
