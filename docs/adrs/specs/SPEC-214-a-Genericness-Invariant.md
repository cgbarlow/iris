# SPEC-214-a: Genericness invariant

Implements: [ADR-214](../ADR-214-Genericness-Invariant-Shopping-List.md)

## 1. Banned terms

Case-insensitive, word-boundary match (`\b<term>\b`):

```
ingredient, ingredients
recipe, recipes
meal, meals, mealplan
diners
servings
aisle, aisles
grocery, groceries
pantry
shopping
```

## 2. Scanned paths

Two scopes:

- **Backend code**: `backend/app/**/*.py` excluding `backend/app/migrations/`, `backend/app/seed/`, `backend/app/import_sparx/`.
- **Frontend code**: `frontend/src/**/*.{ts,svelte,js}` excluding `frontend/src/lib/i18n/` (if present).

Excluded everywhere:

- `*.md` files (docs/CHANGELOG/README are exempt).
- `**/tests/**`, `**/test_*` files.

## 3. Script (`scripts/check_aggregation_genericness.py`)

```python
#!/usr/bin/env python3
"""Genericness invariant CI check (ADR-214).

Fails CI if any banned domain term (ingredient / recipe / meal /
diners / servings / aisle / grocery / pantry / shopping, case-
insensitive) appears in Iris core code paths.

Run locally:  python3 scripts/check_aggregation_genericness.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

BANNED = [
    "ingredient", "ingredients",
    "recipe", "recipes",
    "meal", "meals", "mealplan",
    "diners",
    "servings",
    "aisle", "aisles",
    "grocery", "groceries",
    "pantry",
    "shopping",
]

# (root, exclude-substrings)
SCAN_TARGETS: list[tuple[Path, tuple[str, ...]]] = [
    (REPO_ROOT / "backend" / "app", (
        "/migrations/", "/seed/", "/import_sparx/",
    )),
    (REPO_ROOT / "frontend" / "src", (
        "/i18n/",
    )),
]

# File-extension filter.
SCAN_EXTS = {".py", ".ts", ".svelte", ".js"}

_BANNED_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in BANNED) + r")\b",
    re.IGNORECASE,
)


def _is_excluded(p: Path, excludes: tuple[str, ...]) -> bool:
    s = str(p)
    return any(ex in s for ex in excludes) or "/tests/" in s or "/test_" in s


def main() -> int:
    violations: list[tuple[Path, int, str]] = []
    for root, excludes in SCAN_TARGETS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in SCAN_EXTS:
                continue
            if _is_excluded(path, excludes):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            for line_idx, line in enumerate(text.splitlines(), start=1):
                m = _BANNED_RE.search(line)
                if m:
                    violations.append((path, line_idx, line.strip()))
    if violations:
        print("Genericness invariant violations (ADR-214):", file=sys.stderr)
        for path, line_idx, line in violations:
            rel = path.relative_to(REPO_ROOT)
            print(f"  {rel}:{line_idx}: {line}", file=sys.stderr)
        print(
            f"\nTotal: {len(violations)} violations across "
            f"{len({v[0] for v in violations})} files.",
            file=sys.stderr,
        )
        return 1
    print("Genericness invariant clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## 4. GitHub Actions workflow

`.github/workflows/genericness-check.yml`:

```yaml
name: genericness-check

on:
  pull_request:
    paths:
      - 'backend/app/**'
      - 'frontend/src/**'
      - 'scripts/check_aggregation_genericness.py'
      - '.github/workflows/genericness-check.yml'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  genericness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run genericness check
        run: python3 scripts/check_aggregation_genericness.py
```

## 5. Pytest harness

`backend/tests/test_aggregation/test_genericness_invariant.py`:

```python
"""Genericness invariant CI guard (ADR-214). The pytest harness lets
local test runs catch violations before they hit CI."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_genericness_invariant_passes():
    result = subprocess.run(
        ["python3", "scripts/check_aggregation_genericness.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Genericness invariant violation:\n{result.stderr or result.stdout}"
    )
```

## 6. Adding a deliberate exception

If a future use case genuinely needs one of the banned words in a non-domain context, the process is:

1. Open a new ADR superseding the relevant section of ADR-214.
2. Update `SCAN_TARGETS` in the script with the new allow-listed path.
3. Document the reason in the ADR.

This is intentional friction — the check is a tripwire on a strong principle.

## 7. Allow-list rationale

| Excluded path | Why |
|---|---|
| `backend/app/migrations/` | Migration files seed domain data (template names, profile names, descriptions); the words appear in seed strings, not in code paths. |
| `backend/app/seed/` | Seeders for example models; may include domain examples. |
| `backend/app/import_sparx/` | Pre-existing Sparx EA import path; unrelated to issue #211. |
| `frontend/src/lib/i18n/` | (Future) translation strings — UI text legitimately uses domain words. |
| `*.md` | ADRs, specs, READMEs, CHANGELOGs. |
| `**/tests/**`, `test_*` | Tests reference seeded names verbatim. |
