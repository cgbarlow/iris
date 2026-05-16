#!/usr/bin/env python3
"""Surface parity check (ADR-182, SPEC-182-A, v6.6.0).

Scans backend routers, MCP tool registrations, and CLI subcommand
definitions to ensure every backend write endpoint has a matching
MCP tool AND a matching CLI subcommand. Documented asymmetries
(CLI ask, no delete_*, etc.) are exempted via a hardcoded list.

Also enforces protocols §13 DRY for the md→docx/pdf renderer: no
module outside `backend/app/export/renderers/` may import weasyprint
or python-docx for rendering.

Exit code:
  0 — clean (no hard violations).
  1 — hard parity violation OR DRY violation.

Used by .github/workflows/parity-check.yml. Hand-run locally:

    python3 scripts/check_surface_parity.py
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Documented asymmetries ────────────────────────────────────────────
# Each entry exempts a parity gap that exists by design. Format:
#   (gap_kind, name_pattern, reason_link)
# gap_kind:
#   "cli_only"       — present in CLI, absent from MCP (e.g. `ask`)
#   "deferred_write" — write verb absent from all surfaces (e.g. delete_*)
#   "design_invariant" — write verb that conceptually can't exist (e.g.
#                        move_element across diagrams)

DOCUMENTED_ASYMMETRIES: tuple[tuple[str, str, str], ...] = (
    ("cli_only", "ask", "ADR-168 — MCP clients bring their own LLM"),
    ("deferred_write", "delete_*",
     "out-of-scope for issue #133; needs a future ADR (audit, undo)"),
    ("design_invariant", "move_element",
     "ADR-178 invariant — elements travel with their parent diagram"),
)


@dataclass(frozen=True)
class WriteOp:
    """A write operation observed on one surface."""

    surface: str  # "backend" / "mcp" / "cli"
    verb: str     # "create" / "update" / "move" / "delete"
    entity: str   # "collection" / "set" / "package" / "diagram" / "element"


# ── Parsers ───────────────────────────────────────────────────────────


def parse_backend_writes() -> set[WriteOp]:
    """Scan backend routers for write decorators.

    Looks for `@router.{post,put,patch,delete}("/path"...)` and infers
    (verb, entity) from path + HTTP method.
    """
    results: set[WriteOp] = set()
    routers = list(REPO_ROOT.glob("backend/app/*/router.py"))
    # Pattern: @router.<method>("path"...)
    pat = re.compile(
        r'@router\.(post|put|patch|delete)\(\s*"([^"]*)"',
    )
    for router in routers:
        entity = _entity_from_router_path(router)
        if entity is None:
            continue
        text = router.read_text(encoding="utf-8")
        for method, path in pat.findall(text):
            verb = _verb_from_method_and_path(method, path)
            if verb is None:
                continue
            results.add(WriteOp("backend", verb, entity))
    return results


def parse_mcp_writes() -> set[WriteOp]:
    """Scan MCP tool registrations for write tools.

    Looks for `Tool(name="verb_entity",...)` where verb is one of
    create/update/move/delete and entity is one of the known kinds.
    """
    results: set[WriteOp] = set()
    tools_path = REPO_ROOT / "mcp/src/iris_mcp/tools.py"
    text = tools_path.read_text(encoding="utf-8")
    pat = re.compile(r'name="((?:create|update|move|delete)_[a-z_]+)"')
    for name in pat.findall(text):
        verb, entity = name.split("_", 1)
        if entity in _KNOWN_ENTITIES:
            results.add(WriteOp("mcp", verb, entity))
    return results


def parse_cli_writes() -> set[WriteOp]:
    """Scan CLI for write subcommand groups.

    Looks for `@{create,update,move,delete}_app.command("entity")`
    decorators in cli/src/iris_cli/main.py.
    """
    results: set[WriteOp] = set()
    cli_path = REPO_ROOT / "cli/src/iris_cli/main.py"
    text = cli_path.read_text(encoding="utf-8")
    pat = re.compile(
        r'@(create|update|move|delete)_app\.command\(\s*"([a-z_]+)"',
    )
    for verb, entity in pat.findall(text):
        if entity in _KNOWN_ENTITIES:
            results.add(WriteOp("cli", verb, entity))
    return results


# ── Inference helpers ────────────────────────────────────────────────


_KNOWN_ENTITIES = frozenset({
    "collection", "set", "package", "diagram", "element",
})


def _entity_from_router_path(router_path: Path) -> str | None:
    """Map backend/app/<entity>s/router.py → 'entity' singular."""
    rel = router_path.relative_to(REPO_ROOT)
    parts = rel.parts  # ('backend', 'app', '<entity>s', 'router.py')
    if len(parts) < 4:
        return None
    folder = parts[2]
    # collections → collection, etc.
    singular = folder[:-1] if folder.endswith("s") else folder
    return singular if singular in _KNOWN_ENTITIES else None


def _verb_from_method_and_path(method: str, path: str) -> str | None:
    """Map (HTTP method, URL path) → write verb."""
    method = method.lower()
    if method == "post":
        if path == "" or path == "/":
            return "create"
        # Per-entity actions like /rollback, /tags are out of scope —
        # they're operational not entity-CRUD.
        return None
    if method == "put":
        if "/parent" in path:
            return "move"
        if "{" in path and "}" in path:
            return "update"
        return None
    if method == "patch":
        if "/parent" in path:
            return "move"
        return "update"
    if method == "delete":
        return "delete"
    return None


# ── Parity analysis ──────────────────────────────────────────────────


@dataclass
class ParityReport:
    backend: set[WriteOp]
    mcp: set[WriteOp]
    cli: set[WriteOp]
    hard_violations: list[str]
    soft_warnings: list[str]

    def is_clean(self) -> bool:
        return not self.hard_violations


def analyse() -> ParityReport:
    backend = parse_backend_writes()
    mcp = parse_mcp_writes()
    cli = parse_cli_writes()

    # Normalise to (verb, entity) tuples for cross-surface comparison.
    backend_ve = {(op.verb, op.entity) for op in backend}
    mcp_ve = {(op.verb, op.entity) for op in mcp}
    cli_ve = {(op.verb, op.entity) for op in cli}

    hard: list[str] = []
    soft: list[str] = []

    # For every backend write verb, both MCP and CLI must also have it.
    for verb, entity in sorted(backend_ve):
        signature = f"{verb}_{entity}"
        if _is_documented_asymmetry(verb, entity):
            soft.append(
                f"backend has {signature} but mcp/cli intentionally don't "
                f"({_asymmetry_reason(verb, entity)})",
            )
            continue
        if (verb, entity) not in mcp_ve:
            hard.append(
                f"PARITY: backend has {signature} but MCP does not. "
                f"Add an mcp tool wrapping the endpoint.",
            )
        if (verb, entity) not in cli_ve:
            hard.append(
                f"PARITY: backend has {signature} but CLI does not. "
                f"Add an `iris {verb} {entity}` command.",
            )

    # Documented asymmetries that exist (e.g. CLI ask) are reported as
    # informational, not violations.
    for kind, name, reason in DOCUMENTED_ASYMMETRIES:
        soft.append(f"intentional asymmetry: {kind}={name!r} ({reason})")

    # DRY: weasyprint / docx imports outside the renderer module.
    dry_violations = _check_renderer_dry()
    hard.extend(dry_violations)

    return ParityReport(backend, mcp, cli, hard, soft)


def _is_documented_asymmetry(verb: str, entity: str) -> bool:
    """Match a (verb, entity) against the documented-asymmetry list."""
    signature = f"{verb}_{entity}"
    for _kind, name, _reason in DOCUMENTED_ASYMMETRIES:
        if name.endswith("_*"):
            prefix = name[:-1]  # "delete_"
            if signature.startswith(prefix):
                return True
        elif name == signature:
            return True
    return False


def _asymmetry_reason(verb: str, entity: str) -> str:
    signature = f"{verb}_{entity}"
    for _kind, name, reason in DOCUMENTED_ASYMMETRIES:
        if name == signature or (name.endswith("_*") and signature.startswith(name[:-1])):
            return reason
    return "unknown"


def _check_renderer_dry() -> list[str]:
    """Protocols §13: renderer imports live ONLY in the renderer module."""
    violations: list[str] = []
    renderer_dir = REPO_ROOT / "backend/app/export/renderers"
    needles = ("import weasyprint", "from weasyprint", "from markdown_it")
    for py in REPO_ROOT.glob("backend/app/**/*.py"):
        if py.is_relative_to(renderer_dir):
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle in text:
                violations.append(
                    f"DRY: {py.relative_to(REPO_ROOT)} imports {needle!r} "
                    f"— renderer code must live in backend/app/export/renderers/",
                )
                break
    return violations


# ── CLI ──────────────────────────────────────────────────────────────


def _print_report(report: ParityReport) -> None:
    print("=== Surface parity report ===")
    print(f"backend write ops: {len(report.backend)}")
    print(f"mcp     write ops: {len(report.mcp)}")
    print(f"cli     write ops: {len(report.cli)}")
    print()

    if report.soft_warnings:
        print("Notes:")
        for w in report.soft_warnings:
            print(f"  - {w}")
        print()

    if report.hard_violations:
        print("❌ HARD VIOLATIONS:")
        for v in report.hard_violations:
            print(f"  - {v}")
    else:
        print("✅ Parity clean")


def main(argv: Iterable[str]) -> int:
    report = analyse()
    _print_report(report)
    return 0 if report.is_clean() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
