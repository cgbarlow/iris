"""v6.0.6 (ADR-167): orient-wrapper injection into mcp_system_context.

claude.ai's hosted MCP integration does not reliably surface
`InitializeResult.instructions` to the model (issue #119 testing
post-v6.0.5). v6.0.6's pragmatic fix re-embeds the orient-first
directive directly into the tool RESPONSE, prepended to any non-empty
`mcp_system_context` field — where the model has consistently been
shown to read it.

The wrapper:
- Says "[ORIENT — DO THESE STEPS BEFORE RESPONDING]" up front so the
  model knows the block is a directive, not data.
- Lists the three orient steps imperatively.
- Pre-fills the scope's id (set_id / collection_id) so the model has
  the exact tool-call signature in hand.
- Negates the failure modes explicitly ("DO NOT ask 'want me to load
  it?'", "Do not paraphrase the menu").
- Is idempotent — re-wrapping doesn't double-prepend.
"""

from __future__ import annotations

import json

from iris_mcp.links import (
    with_web_url,
    with_web_urls_list,
    with_web_urls_search,
    wrap_orient,
)

WEB = "https://iris-uat.chrisbarlow.nz"
_MARKER = "[ORIENT"


class TestWrapOrient:
    """`wrap_orient` is the in-place primitive used by every links.py
    surface that emits scope dicts to the wire."""

    def test_wraps_set_with_mcp_system_context(self) -> None:
        item = {
            "id": "33032180-d77a-4ce4-88cf-b49cd643e093",
            "name": "Outcomes Theory Book",
            "mcp_system_context": "Structural overview call: package_hierarchy(set_id=).",
        }
        wrap_orient(item, "set")
        ctx = item["mcp_system_context"]
        assert ctx.startswith(_MARKER)
        # The original body is preserved at the tail.
        assert ctx.endswith(
            "Structural overview call: package_hierarchy(set_id=).",
        )
        # The set_id is pre-filled so the model has the exact call.
        assert 'set_id="33032180-d77a-4ce4-88cf-b49cd643e093"' in ctx
        # The strong directives are present.
        assert "INVOKE" in ctx
        assert "TOC is mandatory" in ctx
        assert "Do not paraphrase" in ctx
        assert "want me to load" in ctx  # explicit anti-pattern call-out

    def test_wraps_collection_with_collection_id_kw(self) -> None:
        item = {
            "id": "b302d473-cad6-4145-8391-d05b5a29c42c",
            "name": "DoView Collection",
            "mcp_system_context": "Top-level collection of DoView material.",
        }
        wrap_orient(item, "collection")
        # For a collection, the wrapper says collection_id (not set_id).
        assert (
            'collection_id="b302d473-cad6-4145-8391-d05b5a29c42c"'
            in item["mcp_system_context"]
        )

    def test_noop_when_mcp_system_context_missing(self) -> None:
        item = {"id": "x", "name": "no context"}
        wrap_orient(item, "set")
        assert "mcp_system_context" not in item

    def test_noop_when_mcp_system_context_empty(self) -> None:
        item = {"id": "x", "mcp_system_context": ""}
        wrap_orient(item, "set")
        # Empty value passes through untouched — no wrapper to prepend
        # on top of nothing.
        assert item["mcp_system_context"] == ""

    def test_noop_when_mcp_system_context_whitespace(self) -> None:
        item = {"id": "x", "mcp_system_context": "   \n  "}
        wrap_orient(item, "set")
        assert item["mcp_system_context"] == "   \n  "

    def test_idempotent_does_not_double_wrap(self) -> None:
        item = {
            "id": "s1",
            "mcp_system_context": "Original body.",
        }
        wrap_orient(item, "set")
        first = item["mcp_system_context"]
        wrap_orient(item, "set")  # second pass
        assert item["mcp_system_context"] == first

    def test_noop_when_id_missing(self) -> None:
        item = {"name": "no id", "mcp_system_context": "body"}
        wrap_orient(item, "set")
        # Without an id we can't pre-fill the tool-call signature, so
        # leave the body alone rather than emit an incomplete wrapper.
        assert item["mcp_system_context"] == "body"


class TestSearchResponseWrap:
    """The orient wrapper must be applied to set/collection results in
    the search response — that's the path the user's claude.ai trace
    in issue #119 hits."""

    def test_search_wraps_set_result(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "query": "outcomes theory",
            "results": [{
                "result_type": "set",
                "id": "33032180-d77a-4ce4-88cf-b49cd643e093",
                "name": "Outcomes Theory Book",
                "mcp_system_context": "MENU: 1. Pull up chapter. 2. Ask. 3. Generate. 4. Browse.",
            }],
        })
        out = json.loads(with_web_urls_search(payload))
        ctx = out["results"][0]["mcp_system_context"]
        assert ctx.startswith(_MARKER)
        # Original body preserved at the tail.
        assert ctx.endswith("4. Browse.")
        # Specific set_id pre-filled.
        assert 'set_id="33032180-d77a-4ce4-88cf-b49cd643e093"' in ctx

    def test_search_wraps_collection_result(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "query": "x",
            "results": [{
                "result_type": "collection",
                "id": "c1",
                "name": "C1",
                "mcp_system_context": "Some collection-scoped orient.",
            }],
        })
        out = json.loads(with_web_urls_search(payload))
        ctx = out["results"][0]["mcp_system_context"]
        assert ctx.startswith(_MARKER)
        assert 'collection_id="c1"' in ctx

    def test_search_does_not_wrap_diagram_result(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        # Diagrams etc. never carry mcp_system_context, so even if a
        # rogue server set it the wrapper should be a no-op on non-
        # scope kinds. (Defence in depth — the v5.x design intent is
        # that only sets and collections own this column.)
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "query": "x",
            "results": [{
                "result_type": "diagram",
                "id": "d1",
                "name": "D1",
                "mcp_system_context": "stray content",
            }],
        })
        out = json.loads(with_web_urls_search(payload))
        # No wrapper for diagram kind.
        ctx = out["results"][0]["mcp_system_context"]
        assert not ctx.startswith(_MARKER)
        assert ctx == "stray content"

    def test_search_skips_results_without_mcp_system_context(
        self, monkeypatch,
    ) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "query": "x",
            "results": [{
                "result_type": "set",
                "id": "s1",
                "name": "S1",
                "mcp_system_context": None,
            }, {
                "result_type": "set",
                "id": "s2",
                "name": "S2",
                # field absent entirely
            }],
        })
        out = json.loads(with_web_urls_search(payload))
        # Both results pass through cleanly with no wrapper.
        for r in out["results"]:
            assert r.get("mcp_system_context") in (None, "")
            # absence stays absence
            if "mcp_system_context" not in r:
                pass


class TestListResponseWrap:
    """list_sets / list_collections return arrays of scopes. Same
    wrapper applies; same idempotency."""

    def test_list_sets_wraps_each_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps([
            {
                "id": "s1", "name": "S1",
                "mcp_system_context": "S1 body",
            },
            {
                "id": "s2", "name": "S2",
                "mcp_system_context": "S2 body",
            },
            {
                "id": "s3", "name": "S3",
                # no mcp_system_context — no wrapper
            },
        ])
        out = json.loads(with_web_urls_list(payload, "set"))
        assert out[0]["mcp_system_context"].startswith(_MARKER)
        assert 'set_id="s1"' in out[0]["mcp_system_context"]
        assert out[0]["mcp_system_context"].endswith("S1 body")
        assert out[1]["mcp_system_context"].startswith(_MARKER)
        assert 'set_id="s2"' in out[1]["mcp_system_context"]
        # Third entry untouched (no field to wrap).
        assert "mcp_system_context" not in out[2]


class TestSingleEntityWrap:
    """get_set / get_collection return one dict; the wrapper applies."""

    def test_with_web_url_wraps_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "id": "s1",
            "name": "S1",
            "mcp_system_context": "body",
        })
        out = json.loads(with_web_url(payload, "set"))
        assert out["mcp_system_context"].startswith(_MARKER)
        assert 'set_id="s1"' in out["mcp_system_context"]

    def test_with_web_url_wraps_collection(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        payload = json.dumps({
            "id": "c1",
            "name": "C1",
            "mcp_system_context": "body",
        })
        out = json.loads(with_web_url(payload, "collection"))
        assert 'collection_id="c1"' in out["mcp_system_context"]


class TestWrapperHappensEvenWithoutIrisWebUrl:
    """The web-URL decoration is gated on IRIS_WEB_URL being set, but
    the orient wrapper must run regardless — the model needs the
    directive in every deployment, including local dev that hasn't
    configured the front-end URL."""

    def test_search_wraps_even_without_iris_web_url(
        self, monkeypatch,
    ) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        payload = json.dumps({
            "query": "x",
            "results": [{
                "result_type": "set",
                "id": "s1",
                "name": "S1",
                "mcp_system_context": "body",
            }],
        })
        out = json.loads(with_web_urls_search(payload))
        # Wrapper applied. web_url decoration is naturally skipped.
        assert out["results"][0]["mcp_system_context"].startswith(_MARKER)
        assert "web_url" not in out["results"][0]
