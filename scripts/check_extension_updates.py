#!/usr/bin/env python3
"""v5.5.0 (issue #48): daily extension upgrade scanner.

Queries the deployed iris-api's GET /api/extensions for the actual
installed versions (rather than reading a static manifest), then
queries the GitHub releases API for each github-sourced extension and
opens an issue (deduplicated by title) when a newer release exists.

v5.5.10 (issue #55 follow-up): switched from manifest.json to
live API query so manual upgrades on UAT (which bump the row's
version field) don't keep re-filing the issue. Falls back to
manifest.json if the API is unreachable so the scanner still works
when iris-api is down or before any deploy.

Run via the scheduled `extensions-check` GitHub Action. Manual:

  GITHUB_TOKEN=<gh-pat> \\
  IRIS_API_URL=https://iris-api-gtb3.onrender.com \\
  python scripts/check_extension_updates.py [--dry-run]

When --dry-run is passed, the script prints what it would file but
doesn't call `gh issue create` / `gh issue list`. Used by the unit
test.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = REPO_ROOT / "extensions" / "sources.json"
MANIFEST_PATH = REPO_ROOT / "extensions" / "manifest.json"

ISSUE_TITLE_TEMPLATE = "Upgrade: {name} extension"


def load_sources() -> dict[str, dict[str, object]]:
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8")).get("extensions", {})


def load_manifest() -> dict[str, str]:
    """Fallback when the live API isn't reachable. Useful for the very
    first scanner run before any deploy, or when iris-api is down."""
    if not MANIFEST_PATH.is_file():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("versions", {})


def fetch_deployed_versions(api_url: str) -> dict[str, str] | None:
    """v5.5.10: query the deployed iris-api for the actual installed
    versions of each extension. Returns { extension_id: version } or
    None on failure (so the caller falls back to manifest.json).

    Uses the unauthenticated /api/extensions/public-status endpoint —
    the data (id + version + source URL) isn't sensitive (it's already
    in extensions/sources.json in a public repo), so avoiding an extra
    auth secret in the GitHub Action is the cleaner design.
    """
    if not api_url:
        return None
    url = api_url.rstrip("/") + "/api/extensions/public-status"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"  iris-api {url} returned {exc.code}: {exc.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  Failed to reach iris-api at {url}: {exc.reason}", file=sys.stderr)
        return None
    items = payload.get("items", [])
    return {item["id"]: item.get("version", "0.0.0") for item in items if "id" in item}


def parse_semver(version: str) -> list[int]:
    """Parse a version string into a list of ints, tolerating `v` prefix and prerelease tails."""
    out: list[int] = []
    for chunk in version.lstrip("vV").split("."):
        num = ""
        for c in chunk:
            if c.isdigit():
                num += c
            else:
                break
        out.append(int(num) if num else 0)
    return out


def is_newer(latest: str, installed: str) -> bool:
    a, b = parse_semver(latest), parse_semver(installed)
    while len(a) < len(b):
        a.append(0)
    while len(b) < len(a):
        b.append(0)
    return a > b


def fetch_latest_release(owner: str, repo: str, token: str | None) -> dict[str, str] | None:
    """Return { tag_name, html_url, body } for the latest release, or None."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None  # No releases yet.
        print(f"  GitHub API error {exc.code} for {owner}/{repo}: {exc.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  Failed to reach GitHub API for {owner}/{repo}: {exc.reason}", file=sys.stderr)
        return None
    return {
        "tag_name": payload.get("tag_name") or payload.get("name") or "",
        "html_url": payload.get("html_url", ""),
        "body": payload.get("body") or "",
    }


def open_issue_if_missing(
    *,
    extension_id: str,
    extension_name: str,
    installed: str,
    latest: str,
    release_url: str,
    release_body: str,
    dry_run: bool,
) -> str:
    """Idempotent: opens an issue iff none with the canonical title is open."""
    title = ISSUE_TITLE_TEMPLATE.format(name=extension_id)

    if not dry_run:
        # gh issue list --state=open --search "Upgrade: <id> extension in:title"
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "open",
                "--search", f"{title} in:title",
                "--json", "number,title",
            ],
            capture_output=True, check=False, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                issues = json.loads(result.stdout)
            except json.JSONDecodeError:
                issues = []
            for issue in issues:
                if issue.get("title", "").strip() == title:
                    return f"already-open: #{issue['number']}"

    body = (
        f"## {extension_name} update available\n\n"
        f"- **Installed**: `{installed}`\n"
        f"- **Latest**:    `{latest}`\n"
        f"- **Release**:   {release_url}\n\n"
        f"### Upstream release notes\n\n"
        f"{release_body or '(no release notes provided)'}\n\n"
        f"---\n"
        f"_Filed automatically by `extensions-check` on a daily schedule. "
        f"Closing this issue resets the dedup; the next run will file a "
        f"fresh one if a newer release lands._\n"
    )

    if dry_run:
        print(f"  [dry-run] would open: '{title}'")
        return f"dry-run: would open '{title}'"

    create = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body],
        capture_output=True, check=False, text=True,
    )
    if create.returncode != 0:
        return f"gh issue create failed: {create.stderr.strip()}"
    return f"opened: {create.stdout.strip()}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen, don't call gh.")
    args = parser.parse_args()

    sources = load_sources()
    manifest = load_manifest()
    gh_token = os.environ.get("GITHUB_TOKEN")
    iris_api_url = os.environ.get("IRIS_API_URL", "https://iris-api-gtb3.onrender.com")

    # v5.5.10: prefer live API state via the public-status endpoint.
    # Fall back to the committed manifest only when the API is
    # unreachable.
    deployed = fetch_deployed_versions(iris_api_url)
    if deployed is None:
        print(f"  iris-api unreachable — falling back to {MANIFEST_PATH.name}")
        deployed = manifest
    else:
        print(f"  using live deployed versions from {iris_api_url}")

    exit_code = 0
    for extension_id, src in sources.items():
        if src.get("source_method") != "github":
            continue
        owner = src.get("github_owner")
        repo = src.get("github_repo")
        if not owner or not repo:
            print(f"  skip {extension_id}: missing github_owner/github_repo")
            continue

        installed = deployed.get(extension_id, manifest.get(extension_id, "0.0.0"))
        print(f"checking {extension_id} ({owner}/{repo}) — installed v{installed}")

        latest = fetch_latest_release(owner, repo, token)
        if latest is None or not latest["tag_name"]:
            print(f"  no release found for {owner}/{repo}")
            continue

        latest_tag = latest["tag_name"]
        if not is_newer(latest_tag, installed):
            print(f"  up to date (latest {latest_tag} ≤ installed {installed})")
            continue

        print(f"  → newer release {latest_tag} available")
        result = open_issue_if_missing(
            extension_id=extension_id,
            extension_name=str(src.get("name", extension_id)),
            installed=installed,
            latest=latest_tag,
            release_url=latest["html_url"],
            release_body=latest["body"],
            dry_run=args.dry_run,
        )
        print(f"  {result}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
