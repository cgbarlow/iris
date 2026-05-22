#!/usr/bin/env python3
"""Genericness invariant CI check (ADR-214).

Fails CI if any banned domain term (ingredient / recipe / meal /
diners / servings / aisle / grocery / pantry / shopping, case-
insensitive, word-boundary) appears in **code paths** in
``backend/app/`` (excluding seed/migrations/import_sparx) or
``frontend/src/`` (excluding i18n).

Comments and docstrings are exempt — the principle is "no domain
logic," not "no domain mentions." Tests and seed files are
allow-listed entirely.

Run locally:  python3 scripts/check_aggregation_genericness.py
"""
from __future__ import annotations

import io
import re
import sys
import tokenize
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

SCAN_TARGETS: list[tuple[Path, tuple[str, ...]]] = [
    (REPO_ROOT / "backend" / "app", (
        "/migrations/",
        "/seed/",
        "/import_sparx/",
    )),
    (REPO_ROOT / "frontend" / "src", (
        "/i18n/",
    )),
]

SCAN_EXTS = {".py", ".ts", ".svelte", ".js"}

_BANNED_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in BANNED) + r")\b",
    re.IGNORECASE,
)


def _is_excluded(p: Path, excludes: tuple[str, ...]) -> bool:
    s = str(p)
    if any(ex in s for ex in excludes):
        return True
    return "/tests/" in s or "/test_" in s


def _strip_python_comments_and_docstrings(source: str) -> list[tuple[int, str]]:
    """Return [(line_no, code-only-line)] with comments and string
    tokens removed. Triple-quoted strings (including module/function
    docstrings) and #-comments are stripped."""
    out: dict[int, list[str]] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            if tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                            tokenize.DEDENT, tokenize.ENCODING,
                            tokenize.ENDMARKER):
                continue
            line_no = tok.start[0]
            out.setdefault(line_no, []).append(tok.string)
    except tokenize.TokenizeError:
        # Fall back to raw lines on tokenizer failure (best-effort).
        return [(i + 1, line) for i, line in enumerate(source.splitlines())]
    return [(ln, " ".join(parts)) for ln, parts in sorted(out.items())]


def _strip_ts_svelte_comments(source: str) -> list[tuple[int, str]]:
    """Strip `//` line comments and `/* … */` block comments from
    TS/Svelte/JS source. Svelte `<!-- … -->` HTML comments too."""
    lines = source.splitlines()
    in_block = False
    in_html_comment = False
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(lines, start=1):
        line = raw
        cleaned_parts: list[str] = []
        idx = 0
        while idx < len(line):
            if in_block:
                end = line.find("*/", idx)
                if end == -1:
                    idx = len(line)
                    break
                idx = end + 2
                in_block = False
                continue
            if in_html_comment:
                end = line.find("-->", idx)
                if end == -1:
                    idx = len(line)
                    break
                idx = end + 3
                in_html_comment = False
                continue
            # Look for next comment opener.
            block_start = line.find("/*", idx)
            line_start = line.find("//", idx)
            html_start = line.find("<!--", idx)
            # Pick earliest non-negative.
            candidates = [
                (block_start, "block"),
                (line_start, "line"),
                (html_start, "html"),
            ]
            valid = [(p, k) for p, k in candidates if p != -1]
            if not valid:
                cleaned_parts.append(line[idx:])
                idx = len(line)
                break
            pos, kind = min(valid, key=lambda x: x[0])
            cleaned_parts.append(line[idx:pos])
            if kind == "line":
                idx = len(line)
                break
            if kind == "block":
                in_block = True
                idx = pos + 2
            elif kind == "html":
                in_html_comment = True
                idx = pos + 4
        out.append((i, "".join(cleaned_parts)))
    return out


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
            if path.suffix == ".py":
                code_lines = _strip_python_comments_and_docstrings(text)
            else:
                code_lines = _strip_ts_svelte_comments(text)
            for line_no, line in code_lines:
                m = _BANNED_RE.search(line)
                if m:
                    violations.append((path, line_no, line.strip()))
    if violations:
        print("Genericness invariant violations (ADR-214):", file=sys.stderr)
        for path, line_no, line in violations:
            rel = path.relative_to(REPO_ROOT)
            print(f"  {rel}:{line_no}: {line}", file=sys.stderr)
        print(
            f"\nTotal: {len(violations)} violations across "
            f"{len({v[0] for v in violations})} files.",
            file=sys.stderr,
        )
        print(
            "\nIf the use is legitimate, see ADR-214 §6 for how to add "
            "an allow-listed path.",
            file=sys.stderr,
        )
        return 1
    print("Genericness invariant clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
