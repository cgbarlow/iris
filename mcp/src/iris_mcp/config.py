"""Environment configuration for iris-mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_URL = "http://localhost:8000"


@dataclass(frozen=True)
class McpConfig:
    url: str
    token: str | None


def load() -> McpConfig:
    return McpConfig(
        url=os.environ.get("IRIS_URL", DEFAULT_URL),
        token=os.environ.get("IRIS_TOKEN"),
    )
