"""`iris patch diagram` (ADR-252, SPEC-252-A, v6.51.0, issue #301).

Protocol §14 parity with the MCP ``patch_diagram`` tool.
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
OPS = [{"op": "remove_node", "id": "n2", "cascade_edges": True},
       {"op": "sync_labels", "node_ids": ["n1"]}]
RESULT = {
    "id": "d-1", "current_version": 3, "updated_at": "2026", "applied": 2,
    "results": [{"index": 0, "op": "remove_node", "id": "n2", "removed_edges": []},
                {"index": 1, "op": "sync_labels", "ids": ["n1"], "skipped": []}],
}


def _invoke(*args: str, stdin: str | None = None) -> tuple[int, str, str]:
    result = runner.invoke(app, list(args), input=stdin, catch_exceptions=False)
    return result.exit_code, result.stdout, result.stderr


def _ops_file(tmp_path: Path) -> str:
    f = tmp_path / "ops.json"
    f.write_text(json.dumps({"operations": OPS}), encoding="utf-8")
    return str(f)


class TestPatchDiagram:
    def test_sends_ops_with_expected_version(
        self, respx_mock: respx.Router, tmp_path: Path,
    ) -> None:
        route = respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=RESULT),
        )
        code, out, _ = _invoke(
            "patch", "diagram", "d-1", "--from-json", _ops_file(tmp_path),
            "--expected-version", "2", "--change-summary", "tidy",
        )
        assert code == 0
        req = route.calls[0].request
        assert req.headers["If-Match"] == "2"
        assert json.loads(req.content) == {"operations": OPS, "change_summary": "tidy"}
        assert json.loads(out)["current_version"] == 3

    def test_reads_stdin_without_expected_version(self, respx_mock: respx.Router) -> None:
        route = respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=RESULT),
        )
        code, _, _ = _invoke(
            "patch", "diagram", "d-1", "--from-json", "-",
            stdin=json.dumps({"operations": OPS}),
        )
        assert code == 0
        req = route.calls[0].request
        assert "If-Match" not in req.headers
        assert json.loads(req.content) == {"operations": OPS}

    def test_failed_op_exits_nonzero_with_message(
        self, respx_mock: respx.Router, tmp_path: Path,
    ) -> None:
        msg = "operations[0] (remove_node): node 'n2' does not exist"
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(422, json={"detail": {
                "error": "operation_failed", "op_index": 0, "op": "remove_node",
                "message": msg,
            }}),
        )
        code, _, err = _invoke("patch", "diagram", "d-1", "--from-json", _ops_file(tmp_path))
        assert code == 1
        assert msg in err

    def test_payload_needs_operations_array(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"ops": OPS}), encoding="utf-8")
        code, _, err = _invoke("patch", "diagram", "d-1", "--from-json", str(f))
        assert code == 1
        assert "operations" in err
