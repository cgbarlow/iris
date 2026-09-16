"""Guard the MCP SDK major-version cap (ADR-244).

The iris-mcp service image installs with plain ``pip install ./mcp`` (no
lockfile), so an unbounded ``mcp>=1.2`` silently resolved to ``mcp`` 2.x on
the v6.48.0 rebuild. SDK 2.x removed the low-level ``Server.list_tools()``
decorator family that ``iris_mcp.server.build_server`` is written against,
and the service crashed at startup. Until the server is ported to the 2.x
API (its own ADR), the dependency must exclude the next major.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _mcp_requirement() -> Requirement:
    deps = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    reqs = [Requirement(d) for d in deps]
    return next(r for r in reqs if r.name == "mcp")


def test_mcp_dependency_excludes_sdk_v2() -> None:
    spec = _mcp_requirement().specifier
    assert not spec.contains(Version("2.0.0"))
    assert not spec.contains(Version("2.2.0"))


def test_mcp_dependency_still_allows_v1() -> None:
    spec = _mcp_requirement().specifier
    assert spec.contains(Version("1.2.0"))


def test_installed_sdk_exposes_low_level_decorators() -> None:
    # The exact API build_server() relies on; fails fast in CI/dev if a
    # 2.x SDK ever gets installed despite the pin.
    from mcp.server.lowlevel import Server

    server = Server("pin-check")
    for name in (
        "list_tools",
        "call_tool",
        "list_resources",
        "read_resource",
        "list_prompts",
        "get_prompt",
    ):
        assert callable(getattr(server, name, None)), name
