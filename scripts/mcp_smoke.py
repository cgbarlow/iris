#!/usr/bin/env -S uv run python
"""End-to-end smoke for the /mcp HTTP route (ADR-133).

Run against a live backend (default http://127.0.0.1:8001) — boots
nothing itself. Prints PASS/FAIL for: initialize handshake, tools/list
returns the expected inventory, tools/call for `search` round-trips.

Usage:
    python scripts/mcp_smoke.py [--url http://...] [--token iris_pat_...]
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx

_HEADERS = {"accept": "application/json, text/event-stream"}


async def _post(client: httpx.AsyncClient, body: dict) -> dict:
    r = await client.post("/mcp/", json=body, headers=_HEADERS)
    r.raise_for_status()
    return r.json()


async def main(url: str, token: str | None) -> int:
    headers: dict[str, str] = {**_HEADERS}
    if token:
        headers["authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(base_url=url, headers=headers, timeout=15) as c:
        # 1. initialize
        init = await _post(c, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "0.1"},
            },
        })
        info = init["result"]["serverInfo"]
        print(f"PASS initialize -> {info['name']} {info['version']}")

        # 2. tools/list
        listed = await _post(c, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = [t["name"] for t in listed["result"]["tools"]]
        for expected in ("search", "get_diagram", "ask"):
            assert expected in tools, f"missing tool {expected}"
        print(f"PASS tools/list -> {len(tools)} tools")

        # 3. tools/call search
        called = await _post(c, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "anything"}},
        })
        content = called["result"]["content"]
        assert content and "text" in content[0]
        print("PASS tools/call(search) -> ok")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument("--token", default=None)
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.url, args.token)))
