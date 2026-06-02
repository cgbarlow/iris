"""v6.0.3 (issue #115 regression class): assert that every
`iris_<word>` token appearing in any live-data source (seeded
migration bodies, iris-mcp Python constants, canonical paste-ready
docs) corresponds to a real registered MCP tool or is in a small
allowlist of legitimate non-tool strings.

This catches the bug class that bit us in v5.13.0 (introduced
`iris_package_hierarchy` typo) → v6.0.0 (claude.ai's stricter tool
loading made it visible) → v6.0.1/v6.0.2/v6.0.3 (three patch
releases to clean up live data).

If you rename a registered tool or add new content that references
a tool by an `iris_` prefix, this test will tell you exactly which
file is out of sync.

Tool names are parsed statically from `mcp/src/iris_mcp/tools.py`
to keep the backend test suite free of cross-package import deps.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# backend/tests/test_migrations/<file> → up 3 = backend → up 1 = repo root
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def _read(rel_to_repo: str) -> str:
    return (REPO_ROOT / rel_to_repo).read_text(encoding="utf-8")


# ── Allowlists ──────────────────────────────────────────────────────


# iris_-prefixed identifiers legitimately referenced in live-data
# bodies but NOT MCP tool names. Env vars, config keys, the server
# name itself, etc.
_NON_TOOL_ALLOWLIST = frozenset({
    "iris_url",
    "iris_token",
    "iris_pat",
    "iris_web_url",
    "iris_api_url",
    "iris_mcp",
    "iris_mcp_public_url",
    "iris_client",  # iris-client import / class name
})


# ── Live-data sources ──────────────────────────────────────────────


# Migration files whose seeded prompt_text becomes live row content.
_LIVE_DATA_MIGRATION_PATHS = (
    "backend/app/migrations/m028_ai_creation_prompts.py",
    "backend/app/migrations/m051_response_format_prompts.py",
    "backend/app/migrations/m053_mcp_server_instructions_seed.py",
    "backend/app/migrations/supabase/m057_mcp_server_instructions_seed.sql",
)


# Canonical paste-ready docs admins copy into live `mcp_system_context`
# fields. We scan only the FIRST ```text fenced block to avoid false
# positives from revision-history prose.
_LIVE_DATA_CANONICAL_DOCS = (
    "docs/prompts/mcp-server-instructions.md",
    "docs/prompts/doview-book-mcp-system-context.md",
)


# iris-mcp source files whose constants ship out as tool descriptions
# / fallback server instructions. Same scan rules apply.
_IRIS_MCP_SOURCE_FILES = (
    "mcp/src/iris_mcp/tools.py",
    "mcp/src/iris_mcp/server_instructions.py",
)


# ── Helpers ─────────────────────────────────────────────────────────


def _registered_tool_names() -> frozenset[str]:
    """Parse `Tool(name="...")` registrations from iris-mcp's tools.py.
    Source of truth for the set of currently-registered MCP tools."""
    src = _read("mcp/src/iris_mcp/tools.py")
    return frozenset(re.findall(r'Tool\(\s*name="([a-z_][a-z0-9_]*)"', src))


def _extract_iris_tokens(body: str) -> set[str]:
    """Pull all `iris_<word>` tokens out of body, lower-cased.

    Word-boundary anchored so the claude.ai display format
    `mcp__iris__<tool>` does NOT match (the inner `iris` is preceded
    by `_` which is a word character — no word boundary)."""
    return set(re.findall(r"\biris_[a-z][a-z0-9_]*\b", body.lower()))


def _extract_canonical_paste_block(md: str) -> str:
    """Extract the body inside the FIRST ```text ... ``` fenced block
    in a canonical paste-ready .md file. That's the only part admins
    paste into live fields; everything else is exempt."""
    m = re.search(r"```text\n(.*?)\n```", md, re.DOTALL)
    return m.group(1) if m else ""


def _violations(body: str, registered: frozenset[str]) -> list[str]:
    tokens = _extract_iris_tokens(body)
    # The registered tool names DO NOT have the `iris_` prefix —
    # claude.ai's display format injects the namespace. Authors
    # often write `iris_<tool>` in prose. So a token like
    # `iris_search` is legitimate iff `search` is a registered tool.
    return sorted(
        tok for tok in tokens
        if tok not in _NON_TOOL_ALLOWLIST
        and tok.removeprefix("iris_") not in registered
    )


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", _LIVE_DATA_MIGRATION_PATHS)
def test_seeded_migration_body_references_only_registered_tools(path: str) -> None:
    """Every `iris_<word>` token in a seeded migration body must be
    either a registered MCP tool (after stripping `iris_` prefix)
    or a known non-tool identifier."""
    registered = _registered_tool_names()
    body = _read(path)
    violations = _violations(body, registered)
    assert not violations, (
        f"{path} references iris_-prefixed names that aren't "
        f"registered MCP tools or in the non-tool allowlist: "
        f"{violations}. If you renamed/removed a tool, update this "
        "file's seed body AND add a fix migration for live data "
        "already seeded with the old name."
    )


@pytest.mark.parametrize("path", _IRIS_MCP_SOURCE_FILES)
def test_iris_mcp_source_files_reference_only_registered_tools(path: str) -> None:
    """The hardcoded Python constants in iris-mcp (fallback baseline,
    tool descriptions, preambles) must reference only registered
    tools. Scans the full file — registered tool names are not
    `iris_`-prefixed so `Tool(name="search")` is not a violation."""
    registered = _registered_tool_names()
    body = _read(path)
    violations = _violations(body, registered)
    assert not violations, (
        f"{path} references iris_-prefixed names that aren't "
        f"registered MCP tools: {violations}."
    )


@pytest.mark.parametrize("path", _LIVE_DATA_CANONICAL_DOCS)
def test_canonical_paste_block_references_only_registered_tools(path: str) -> None:
    """The ```text ... ``` paste block in each canonical doc must
    reference only registered tools. Prose outside that block (e.g.
    revision history) is historical and exempt."""
    registered = _registered_tool_names()
    md = _read(path)
    paste_block = _extract_canonical_paste_block(md)
    if not paste_block:
        pytest.skip(f"no ```text fenced paste block found in {path}")
    violations = _violations(paste_block, registered)
    assert not violations, (
        f"{path} paste block references iris_-prefixed names that "
        f"aren't registered MCP tools: {violations}."
    )


def test_iris_package_hierarchy_specifically_absent_from_all_seeds() -> None:
    """Regression test for issue #115. The structural-overview tool is
    `package_hierarchy`, not `iris_package_hierarchy`. The v5.13.0
    typo lived in canonical content + seeds for five releases."""
    for path in _LIVE_DATA_MIGRATION_PATHS:
        body = _read(path)
        assert "iris_package_hierarchy" not in body, (
            f"{path} still references the non-existent tool "
            "`iris_package_hierarchy` (issue #115 regression)."
        )


def test_iris_authenticate_specifically_absent_from_v6_seeds() -> None:
    """Regression: `iris_authenticate` was removed in v6.0.0 (ADR-164).
    Seeded bodies referencing it would seed fresh installs with
    prompts pointing at a non-existent tool. Surfaced during the
    issue #115 inventory."""
    for path in _LIVE_DATA_MIGRATION_PATHS:
        body = _read(path)
        assert "iris_authenticate" not in body, (
            f"{path} still references the v6.0.0-removed tool "
            "`iris_authenticate` (issue #115 follow-up regression)."
        )


def test_allowlist_does_not_mask_a_registered_tool() -> None:
    """Sanity: nothing in the non-tool allowlist should accidentally
    match a registered MCP tool name. If iris-mcp ever adds a tool
    literally named `url` (making `iris_url` ambiguous), flag it
    before the other tests silently green-light it."""
    registered = _registered_tool_names()
    overlap = {
        item for item in _NON_TOOL_ALLOWLIST
        if item.removeprefix("iris_") in registered
    }
    assert not overlap, (
        f"Non-tool allowlist entries overlap with registered MCP "
        f"tools: {overlap}. Remove from allowlist or rename the tool."
    )


def test_registered_tool_names_parse_correctly() -> None:
    """Smoke test for the registered-name parser. If iris-mcp's tool
    registration syntax ever drifts away from `Tool(name="...")`, we
    catch it here rather than silently emptying the allowlist."""
    registered = _registered_tool_names()
    # Known anchor tools that have been registered since v5.x — if
    # this set ever drops one, the parser is broken or a tool was
    # genuinely removed (in which case update the anchor list).
    # NB: `ask` is deliberately NOT here — it is a CLI-only command
    # (ADR-168: MCP clients bring their own LLM), so it is never a
    # registered MCP tool. Anchor only on real MCP tools.
    anchors = {"search", "package_hierarchy", "create_diagram", "create_collection"}
    missing = anchors - registered
    assert not missing, (
        f"Tool name parser couldn't find expected anchor tools: "
        f"{missing}. Either iris-mcp tool registration syntax "
        "changed or these tools were removed."
    )
