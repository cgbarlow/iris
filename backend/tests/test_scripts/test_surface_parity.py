"""Protocol §14 surface parity for relationships (ADR-249, v6.50.0, #298).

`scripts/check_surface_parity.py` only enforces entities listed in
``_KNOWN_ENTITIES``. ADR-249 adds ``relationship`` so the relationship
write routes must have a matching MCP tool AND CLI subcommand, and teaches
the checker to attribute batch routes (``/api/batch/<entities>/<verb>``) and
plural batch tool / command names (``create_relationships``) to their entity.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load() -> object:
    spec = importlib.util.spec_from_file_location(
        "check_surface_parity", REPO_ROOT / "scripts" / "check_surface_parity.py",
    )
    mod = importlib.util.module_from_spec(spec)
    # @dataclass resolves its module via sys.modules.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_relationship_is_a_known_entity() -> None:
    mod = _load()
    assert "relationship" in mod._KNOWN_ENTITIES  # type: ignore[attr-defined]


def test_batch_route_attribution() -> None:
    mod = _load()
    op = mod._batch_route_op  # type: ignore[attr-defined]
    assert op("post", "/relationships/create") == ("create", "relationship")
    assert op("post", "/elements/update") == ("update", "element")
    assert op("post", "/diagrams/delete") == ("delete", "diagram")
    # Operational batch actions are not entity CRUD.
    assert op("post", "/elements/clone") is None
    assert op("post", "/elements/tags") is None


def test_plural_batch_names_normalise_to_entity() -> None:
    mod = _load()
    norm = mod._normalise_entity  # type: ignore[attr-defined]
    assert norm("relationships") == "relationship"
    assert norm("relationship") == "relationship"
    assert norm("elements") == "element"
    assert norm("aggregation_profiles") is None


def test_relationship_write_parity_on_every_surface() -> None:
    mod = _load()
    report = mod.analyse()  # type: ignore[attr-defined]
    for surface in (report.backend, report.mcp, report.cli):
        ve = {(op.verb, op.entity) for op in surface}
        for verb in ("create", "update", "delete"):
            assert (verb, "relationship") in ve, (verb, surface)
    assert report.hard_violations == []


# ── ADR-252 (v6.51.0, #301): `patch` is its own write verb ────────────


def test_http_patch_is_the_patch_verb() -> None:
    """HTTP PATCH on an entity is an incremental edit (ADR-252), not a full
    update — it must be matched by a ``patch_<entity>`` MCP tool and an
    ``iris patch <entity>`` CLI command, not by ``update_<entity>``."""
    mod = _load()
    verb = mod._verb_from_method_and_path  # type: ignore[attr-defined]
    assert verb("patch", "/{diagram_id}") == "patch"
    # PUT semantics are unchanged.
    assert verb("put", "/{diagram_id}") == "update"
    assert verb("put", "/{diagram_id}/parent") == "move"


def test_patch_diagram_parity_on_every_surface() -> None:
    mod = _load()
    report = mod.analyse()  # type: ignore[attr-defined]
    for surface in (report.backend, report.mcp, report.cli):
        ve = {(op.verb, op.entity) for op in surface}
        assert ("patch", "diagram") in ve, surface
    assert report.hard_violations == []
