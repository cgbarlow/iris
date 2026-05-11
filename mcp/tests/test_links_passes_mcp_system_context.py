"""v5.11.0 / ADR-156: scope `mcp_system_context` is data passthrough.

ADR-151 (v5.8.2) strips `system_prompt` from MCP tool responses
because that column is server-side-only directive content and lets in
prompt-injection vectors when treated as untrusted data. ADR-156
introduces a SECOND scope column, `mcp_system_context`, with the
opposite intent: it is *meant* to flow through MCP tool responses as
initial context for the model when a user is browsing the scope. The
v5.8.2 strip must therefore NOT touch this column.

These tests pin the contract: `mcp_system_context` survives the
links.py boundary unchanged in the same payload shapes the
`system_prompt` tests cover.
"""

from __future__ import annotations

import json

from iris_mcp.links import with_web_url, with_web_urls_list, with_web_urls_search

WEB = "https://iris-uat.chrisbarlow.nz"


class TestMcpSystemContextPassesThrough:
    def test_with_web_url_keeps_mcp_system_context_on_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "id": "set-1", "name": "DoView Book",
            "system_prompt": "Iris-AI only.",
            "mcp_system_context": "MCP browsing context for DoView Book.",
            "description": "Visual companion.",
        })
        out = json.loads(with_web_url(payload, "set"))
        # system_prompt is stripped (ADR-151)…
        assert "system_prompt" not in out
        # …but mcp_system_context passes through (ADR-156).
        assert out["mcp_system_context"] == "MCP browsing context for DoView Book."

    def test_with_web_url_keeps_mcp_system_context_on_collection(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "id": "coll-1", "name": "NZISM",
            "system_prompt": "Iris-AI only.",
            "mcp_system_context": "MCP browsing context for NZISM.",
        })
        out = json.loads(with_web_url(payload, "collection"))
        assert "system_prompt" not in out
        assert out["mcp_system_context"] == "MCP browsing context for NZISM."

    def test_with_web_urls_list_keeps_mcp_system_context_per_item(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps([
            {"id": "s1", "name": "A",
             "system_prompt": "iris-internal-A",
             "mcp_system_context": "mcp-A"},
            {"id": "s2", "name": "B",
             "system_prompt": "iris-internal-B",
             "mcp_system_context": "mcp-B"},
            {"id": "s3", "name": "C"},  # neither column populated
        ])
        out = json.loads(with_web_urls_list(payload, "set"))
        # system_prompt stripped on all, mcp_system_context preserved.
        assert all("system_prompt" not in item for item in out)
        assert out[0]["mcp_system_context"] == "mcp-A"
        assert out[1]["mcp_system_context"] == "mcp-B"
        # Item without the column is unaffected.
        assert "mcp_system_context" not in out[2]

    def test_with_web_urls_search_keeps_mcp_system_context_per_result(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "query": "x",
            "results": [
                {"result_type": "set", "id": "s1", "name": "S1",
                 "system_prompt": "iris-only",
                 "mcp_system_context": "mcp-passthrough"},
                {"result_type": "collection", "id": "c1", "name": "C1",
                 "system_prompt": "iris-only",
                 "mcp_system_context": "coll-passthrough"},
            ],
        })
        out = json.loads(with_web_urls_search(payload))
        for r in out["results"]:
            assert "system_prompt" not in r
        assert out["results"][0]["mcp_system_context"] == "mcp-passthrough"
        assert out["results"][1]["mcp_system_context"] == "coll-passthrough"
