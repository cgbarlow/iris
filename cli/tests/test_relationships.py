"""CLI relationship commands (ADR-249, SPEC-249-A, v6.50.0, issue #298).

Protocol §14 parity with the MCP relationship tools:

- `iris create relationship` / `iris create relationships --from-json`
- `iris update relationship <id>`
- `iris delete relationship <id>`
- `iris relationships list` / `iris relationships get <id>`
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


def _rel(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "r-1", "source_element_id": "a", "target_element_id": "b",
        "relationship_type": "association", "current_version": 2,
        "label": "L", "description": None,
        "data": {"sourceRole": "partner"},
        "source_role": "partner", "target_role": None,
        "created_at": "2026", "created_by": "u", "updated_at": "2026",
        "is_deleted": False,
        "source_element_name": "A", "target_element_name": "B",
    }
    base.update(overrides)
    return base


_OK = {"succeeded": 1, "failed": 0, "errors": [], "ids": ["r-1"]}


class TestCreate:
    def test_create_relationship_single(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(200, json=_OK),
        )
        code, out, _ = _invoke(
            "create", "relationship",
            "--source", "a", "--target", "b", "--type", "association",
            "--source-role", "partner", "--target-role", "child",
            "--label", "L", "--data-json", '{"child_order": 1}',
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body == {"relationships": [{
            "source_element_id": "a", "target_element_id": "b",
            "relationship_type": "association",
            "source_role": "partner", "target_role": "child",
            "label": "L", "data": {"child_order": 1},
        }]}
        assert json.loads(out)["ids"] == ["r-1"]

    def test_create_relationship_rejected_exits_nonzero(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(200, json={
                "succeeded": 0, "failed": 1,
                "errors": ["Relationship at index 0: self-referencing relationships "
                           "are not allowed"],
                "ids": [],
            }),
        )
        code, _out, err = _invoke(
            "create", "relationship",
            "--source", "a", "--target", "a", "--type", "association",
        )
        assert code == 1
        assert "self-referencing" in err

    def test_create_relationships_from_json(
        self, respx_mock: respx.Router, tmp_path: Path,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(200, json=_OK),
        )
        payload = {"relationships": [{
            "source_element_id": "a", "target_element_id": "b",
            "relationship_type": "association",
        }]}
        f = tmp_path / "rels.json"
        f.write_text(json.dumps(payload))
        code, out, _ = _invoke("create", "relationships", "--from-json", str(f))
        assert code == 0
        assert json.loads(route.calls[0].request.content) == payload
        assert json.loads(out)["succeeded"] == 1


class TestUpdate:
    def test_update_relationship_partial(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        put = respx_mock.put(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel(relationship_type="composition")),
        )
        code, out, _ = _invoke(
            "update", "relationship", "r-1",
            "--type", "composition", "--target-role", "child",
        )
        assert code == 0
        req = put.calls[0].request
        assert req.headers["If-Match"] == "2"
        body = json.loads(req.content)
        assert body["relationship_type"] == "composition"
        assert body["target_role"] == "child"
        assert body["label"] == "L"
        assert body["data"] == {"sourceRole": "partner"}
        assert json.loads(out)["relationship_type"] == "composition"


class TestDelete:
    def test_delete_relationship(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        delete = respx_mock.delete(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(204),
        )
        code, out, _ = _invoke("delete", "relationship", "r-1")
        assert code == 0
        assert delete.calls[0].request.headers["If-Match"] == "2"
        assert json.loads(out) == {"deleted": True, "relationship_id": "r-1"}


class TestRead:
    def test_list_json(self, respx_mock: respx.Router) -> None:
        route = respx_mock.get(f"{BASE}/api/relationships").mock(
            return_value=httpx.Response(200, json={
                "items": [_rel()], "total": 1, "page": 1, "page_size": 50,
            }),
        )
        code, out, _ = _invoke(
            "--json", "relationships", "list",
            "--set-id", "s-1", "--type", "association",
        )
        assert code == 0
        params = route.calls[0].request.url.params
        assert params["set_id"] == "s-1"
        assert params["relationship_type"] == "association"
        rows = json.loads(out)
        assert rows[0]["source_role"] == "partner"

    def test_list_table(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships").mock(
            return_value=httpx.Response(200, json={
                "items": [_rel()], "total": 1, "page": 1, "page_size": 50,
            }),
        )
        code, out, _ = _invoke("relationships", "list", "--element-id", "a")
        assert code == 0
        assert "Relationships (1 of 1)" in out
        assert "partner" in out  # role column rendered

    def test_get(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        code, out, _ = _invoke("relationships", "get", "r-1")
        assert code == 0
        assert json.loads(out)["id"] == "r-1"
