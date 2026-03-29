"""MNEMOS client adapter (ADR-111).

Loosely couples Iris to MNEMOS via a protocol boundary. The adapter wraps
the mnemos_sdk client and provides retrieval + indexing methods.

This module is only imported when the MNEMOS extension is enabled.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from app.ai.context import build_multi_set_context, build_set_context
from app.ai.retrieval import DirectRetrieval, RetrievalPort

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

log = logging.getLogger("app.mnemos.adapter")

# Default config values
_DEFAULT_URL = "http://localhost:8700"
_DEFAULT_TIMEOUT_MS = 5000
_DEFAULT_MAX_RESULTS = 50


async def _get_mnemos_config(db: DatabasePort) -> dict[str, object]:
    """Read MNEMOS config from the extensions table."""
    from app.extensions.service import get_extension

    ext = await get_extension(db, "mnemos")
    if ext is None:
        return {}
    config = ext.get("config", {})
    return config if isinstance(config, dict) else {}


class SemanticRetrieval:
    """Retrieves context via MNEMOS semantic search with DirectRetrieval fallback.

    When MNEMOS is unreachable or returns empty results, falls back to
    DirectRetrieval transparently.
    """

    def __init__(self, url: str, timeout_ms: int, max_results: int) -> None:
        self._url = url
        self._timeout_ms = timeout_ms
        self._max_results = max_results
        self._fallback = DirectRetrieval()

    async def retrieve_context(
        self,
        db: DatabasePort,
        question: str,
        set_ids: list[str],
        *,
        max_tokens: int = 8000,
        package_ids: list[str] | None = None,
    ) -> str:
        """Retrieve context via MNEMOS, falling back to direct on failure."""
        print(f"[MNEMOS] Attempting semantic retrieval from {self._url}", flush=True)
        try:
            result = await self._semantic_retrieve(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids,
            )
            print(f"[MNEMOS] Semantic retrieval succeeded ({len(result)} chars)", flush=True)
            return result
        except Exception as exc:  # noqa: BLE001
            print(f"[MNEMOS] Semantic retrieval failed ({exc}) — falling back to DirectRetrieval", flush=True)
            return await self._fallback.retrieve_context(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids,
            )

    async def _semantic_retrieve(
        self,
        db: DatabasePort,
        question: str,
        set_ids: list[str],
        *,
        max_tokens: int = 8000,
        package_ids: list[str] | None = None,
    ) -> str:
        """Query MNEMOS for semantically relevant engrams."""
        try:
            from mnemos_sdk import MnemosClient, MnemosConfig  # type: ignore[import-untyped]
        except ImportError:
            log.debug("mnemos_sdk not installed, falling back to direct retrieval")
            raise  # noqa: TRY201

        config = MnemosConfig(
            base_url=self._url,
            timeout_s=self._timeout_ms / 1000,
        )
        client = MnemosClient(config)

        # Build neuro-tag filters for set scope
        tag_filters = [f"set:{sid}" for sid in set_ids]
        if package_ids:
            tag_filters.extend(f"pkg:{pid}" for pid in package_ids)

        hits = client.search(
            question,
            top_k=self._max_results,
        )

        if not hits:
            # No results — fall back to direct
            return await self._fallback.retrieve_context(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids,
            )

        # Format hits as structured text (same format as context.py output)
        lines = [f"SEMANTIC CONTEXT ({len(hits)} results):\n"]
        for hit in hits:
            engram = hit.engram if hasattr(hit, "engram") else hit
            content = engram.get("content", "") if isinstance(engram, dict) else str(engram)
            score = hit.score if hasattr(hit, "score") else 0.0
            lines.append(f"- [{score:.2f}] {content}")

        return "\n".join(lines)


async def create_semantic_retrieval(db: DatabasePort) -> RetrievalPort:
    """Create a SemanticRetrieval instance from extension config."""
    config = await _get_mnemos_config(db)
    url = str(config.get("url", _DEFAULT_URL))
    timeout_ms = int(config.get("timeout_ms", _DEFAULT_TIMEOUT_MS))
    max_results = int(config.get("max_results", _DEFAULT_MAX_RESULTS))
    return SemanticRetrieval(url, timeout_ms, max_results)


async def check_mnemos_health(url: str) -> bool:
    """Check if MNEMOS service is healthy at the given URL."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            return resp.status_code == 200  # noqa: PLR2004
    except Exception:  # noqa: BLE001
        return False
