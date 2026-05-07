"""Environment configuration for iris-mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_URL = "http://localhost:8000"


@dataclass(frozen=True)
class McpConfig:
    url: str
    token: str | None
    web_url: str | None  # v5.6.1: base URL of the iris web UI; emitted
                         # alongside item ids so the LLM can produce real
                         # links instead of guessing the host.


def load() -> McpConfig:
    raw_web = os.environ.get("IRIS_WEB_URL")
    return McpConfig(
        url=os.environ.get("IRIS_URL", DEFAULT_URL),
        token=os.environ.get("IRIS_TOKEN"),
        web_url=raw_web.rstrip("/") if raw_web else None,
    )
