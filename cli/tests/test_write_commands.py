"""v6.4.0 (ADR-180, SPEC-180-A): CLI write-tool parity tests.

Covers the new sub-apps: `iris create`, `iris update`, `iris move`,
`iris render`. Pattern matches `test_commands.py` — respx-mocked
backend, Typer CliRunner.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from iris_cli.main import app

runner = CliRunner()
BASE = "http://iris.test"


def _invoke(*args: str) -> tuple[int, str, str]:
    result = runner.invoke(app, list(args), catch_exceptions=False)
    return result.exit_code, result.stdout, result.stderr


# ── iris create ────────────────────────────────────────────────────────


class TestCreate:
    def test_create_collection(self, respx_mock: respx.Router) -> None:
        respx_mock.post(f"{BASE}/api/collections").mock(
            return_value=httpx.Response(201, json={
                "id": "c1", "name": "Outcomes", "description": None,
                "created_at": "2026", "updated_at": "2026",
            }),
        )
        code, out, _ = _invoke("create", "collection", "--name", "Outcomes")
        assert code == 0
        assert "c1" in out

    def test_create_set_with_collection(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(f"{BASE}/api/sets").mock(
            return_value=httpx.Response(201, json={
                "id": "s1", "name": "MySet", "collection_id": "c1",
                "description": None,
                "created_at": "2026", "updated_at": "2026",
            }),
        )
        code, out, _ = _invoke(
            "create", "set", "--name", "MySet", "--collection-id", "c1",
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body == {"name": "MySet", "collection_id": "c1"}

    def test_create_package(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(201, json={
                "id": "p1", "name": "Pkg", "current_version": 1,
                "set_id": "s1",
                "created_at": "2026", "updated_at": "2026",
            }),
        )
        code, _out, _ = _invoke(
            "create", "package", "--name", "Pkg",
            "--set-id", "s1",
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body["name"] == "Pkg"
        assert body["set_id"] == "s1"

    def test_create_element(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(201, json={
                "id": "el1", "name": "Widget",
                "element_type": "component",
                "current_version": 1, "notation": "simple", "set_id": "s1",
                "created_at": "2026", "updated_at": "2026", "data": {},
            }),
        )
        code, out, _ = _invoke(
            "create", "element",
            "--name", "Widget", "--element-type", "component",
            "--set-id", "s1", "--notation", "simple",
        )
        assert code == 0
        assert "el1" in out
        body = json.loads(route.calls[0].request.content)
        assert body["element_type"] == "component"
        assert body["name"] == "Widget"
        assert body["set_id"] == "s1"
        assert body["notation"] == "simple"

    def test_create_diagram_with_data_json(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(201, json={
                "id": "d1", "name": "D", "diagram_type": "simple",
                "current_version": 1, "notation": "simple", "set_id": "s1",
                "created_at": "2026", "updated_at": "2026", "data": {},
            }),
        )
        code, _out, _ = _invoke(
            "create", "diagram",
            "--name", "D", "--diagram-type", "simple",
            "--notation", "simple", "--set-id", "s1",
            "--data-json", '{"nodes": [], "edges": []}',
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body["data"] == {"nodes": [], "edges": []}


# ── iris update ────────────────────────────────────────────────────────


def _entity(**overrides):
    base = {
        "id": "e1", "name": "Original Name", "description": "orig",
        "created_at": "2026", "updated_at": "2026",
    }
    base.update(overrides)
    return base


class TestUpdate:
    def test_update_collection_preserves_name(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/collections/c1").mock(
            return_value=httpx.Response(200, json=_entity(id="c1")),
        )
        put_route = respx_mock.put(f"{BASE}/api/collections/c1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="c1", description="new desc",
            )),
        )
        code, _out, _ = _invoke(
            "update", "collection", "c1", "--description", "new desc",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body["name"] == "Original Name"  # preserved from GET
        assert body["description"] == "new desc"  # overridden

    def test_update_set_excludes_collection_id(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/sets/s1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s1", collection_id="col-existing",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s1", name="Renamed",
            )),
        )
        code, _out, _ = _invoke("update", "set", "s1", "--name", "Renamed")
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        # collection_id intentionally NOT in body (move concern).
        assert "collection_id" not in body

    def test_update_diagram_data(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/diagrams/d1").mock(
            return_value=httpx.Response(200, json=_entity(id="d1")),
        )
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d1").mock(
            return_value=httpx.Response(200, json=_entity(id="d1")),
        )
        code, _out, _ = _invoke(
            "update", "diagram", "d1",
            "--data-json", '{"nodes": [{"id": "n1"}], "edges": []}',
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body["data"] == {"nodes": [{"id": "n1"}], "edges": []}

    def test_update_package_no_flags_is_noop_safe(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/packages/p1").mock(
            return_value=httpx.Response(200, json=_entity(id="p1")),
        )
        put_route = respx_mock.put(f"{BASE}/api/packages/p1").mock(
            return_value=httpx.Response(200, json=_entity(id="p1")),
        )
        code, _out, _ = _invoke("update", "package", "p1")
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        # No flags → body is fully sourced from GET.
        assert body["name"] == "Original Name"

    def test_update_element(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_entity(id="el1")),
        )
        respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="el1", description="el desc",
            )),
        )
        code, _out, _ = _invoke(
            "update", "element", "el1", "--description", "el desc",
        )
        assert code == 0


# ── iris move ──────────────────────────────────────────────────────────


class TestMove:
    def test_move_diagram_to_package(self, respx_mock: respx.Router) -> None:
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d1/parent").mock(
            return_value=httpx.Response(200, json={
                "id": "d1", "parent_package_id": "pkg-7",
            }),
        )
        code, _out, _ = _invoke(
            "move", "diagram", "d1", "--to-package", "pkg-7",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body == {"parent_package_id": "pkg-7"}

    def test_move_diagram_to_root_with_null(
        self, respx_mock: respx.Router,
    ) -> None:
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d1/parent").mock(
            return_value=httpx.Response(200, json={"id": "d1"}),
        )
        code, _out, _ = _invoke(
            "move", "diagram", "d1", "--to-package", "null",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body == {"parent_package_id": None}

    def test_move_package_to_parent(self, respx_mock: respx.Router) -> None:
        put_route = respx_mock.put(f"{BASE}/api/packages/p1/parent").mock(
            return_value=httpx.Response(200, json={"id": "p1"}),
        )
        code, _out, _ = _invoke(
            "move", "package", "p1", "--to-parent", "pkg-2",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body == {"parent_package_id": "pkg-2"}

    def test_move_set_to_collection_preserves_metadata(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/sets/s1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s1", name="MySet", description="d",
                collection_id="col-old", system_prompt="sp",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s1", collection_id="col-new",
            )),
        )
        code, _out, _ = _invoke(
            "move", "set", "s1", "--to-collection", "col-new",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body["collection_id"] == "col-new"
        assert body["name"] == "MySet"
        assert body["system_prompt"] == "sp"

    def test_move_set_uncollect(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/sets/s1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s1", collection_id="col-old",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s1").mock(
            return_value=httpx.Response(200, json=_entity(id="s1")),
        )
        code, _out, _ = _invoke(
            "move", "set", "s1", "--to-collection", "null",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert "collection_id" in body
        assert body["collection_id"] is None


# ── iris render ────────────────────────────────────────────────────────


class TestRender:
    def test_render_markdown_metadata_only(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/markdown").mock(
            return_value=httpx.Response(200, json={
                "id": "art-1", "filename": "doc-abc.md",
                "mime_type": "text/markdown", "size_bytes": 5,
                "source_kind": "render_markdown", "source_ref": None,
                "created_at": "2026",
            }),
        )
        # Provide stdin via runner.invoke's input arg.
        result = runner.invoke(
            app,
            ["render", "markdown", "--title", "T", "--format", "md"],
            input="# Hi\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "art-1" in result.stdout

    def test_render_diagram_with_output_downloads_bytes(
        self, respx_mock: respx.Router, tmp_path: Path,
    ) -> None:
        respx_mock.post(f"{BASE}/api/export/diagram/d1").mock(
            return_value=httpx.Response(200, json={
                "id": "art-2", "filename": "d1-xyz.pdf",
                "mime_type": "application/pdf", "size_bytes": 4,
                "source_kind": "export_diagram", "source_ref": "d1",
                "created_at": "2026",
            }),
        )
        respx_mock.get(f"{BASE}/api/artefacts/art-2").mock(
            return_value=httpx.Response(
                200, content=b"%PDF",
                headers={"content-type": "application/pdf"},
            ),
        )
        out = tmp_path / "out.pdf"
        code, _out, _ = _invoke(
            "render", "diagram", "d1", "--format", "pdf", "-o", str(out),
        )
        assert code == 0
        assert out.read_bytes() == b"%PDF"

    def test_render_markdown_from_input_file(
        self, respx_mock: respx.Router, tmp_path: Path,
    ) -> None:
        src = tmp_path / "src.md"
        src.write_text("# From file\n", encoding="utf-8")
        route = respx_mock.post(f"{BASE}/api/export/markdown").mock(
            return_value=httpx.Response(200, json={
                "id": "art-3", "filename": "file-abc.md",
                "mime_type": "text/markdown", "size_bytes": 12,
                "source_kind": "render_markdown", "source_ref": None,
                "created_at": "2026",
            }),
        )
        code, _out, _ = _invoke(
            "render", "markdown", "--title", "From",
            "--format", "md", "--input", str(src),
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body["markdown"] == "# From file\n"
        assert body["title"] == "From"
