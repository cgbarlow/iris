"""MNEMOS client adapter (ADR-111, ADR-113).

Loosely couples Iris to MNEMOS via a protocol boundary. The adapter wraps
the mnemos_sdk client and provides retrieval + indexing methods.

Uses metadata filtering to scope searches by iris_type, preventing
architecture data and legislation chunks from interfering with each other.

This module is only imported when the MNEMOS extension is enabled.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.ai.context import build_multi_set_context, build_set_context
from app.ai.retrieval import DirectRetrieval, RetrievalPort

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

log = logging.getLogger("app.mnemos.adapter")

# Default config values
_DEFAULT_URL = "http://localhost:8700"
_DEFAULT_TIMEOUT_MS = 5000
_DEFAULT_MAX_RESULTS = 50

# Rough heuristic: 4 chars ~ 1 token
_CHARS_PER_TOKEN = 4


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

    Searches are filtered to architecture data only (elements, relationships,
    diagrams) using ChromaDB metadata filters, so DocRef legislation chunks
    in the same index never interfere with set queries.
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
        diagram_ids: list[str] | None = None,
    ) -> str:
        """Retrieve context via MNEMOS, falling back to direct on failure.

        When package_ids or diagram_ids is provided, uses DirectRetrieval
        instead since MNEMOS engrams don't carry scope metadata.
        """
        if package_ids or diagram_ids:
            print("[MNEMOS] Scoped filter active — using DirectRetrieval for scoped context", flush=True)
            return await self._fallback.retrieve_context(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids, diagram_ids=diagram_ids,
            )
        print(f"[MNEMOS] Attempting semantic retrieval from {self._url}", flush=True)
        try:
            # Get both semantic hits and full structural context, then combine.
            # Semantic hits provide question-aware relevance; direct context
            # provides the complete diagram/element/relationship structure the
            # LLM needs for structural questions.
            direct_ctx = await self._fallback.retrieve_context(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids, diagram_ids=diagram_ids,
            )
            result = await self._semantic_retrieve(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids, diagram_ids=diagram_ids,
            )
            # Combine: direct structural context first, then semantic highlights
            combined = direct_ctx + "\n\n---\n\n" + result
            print(f"[MNEMOS] Combined context: direct={len(direct_ctx)} + semantic={len(result)} = {len(combined)} chars", flush=True)
            return combined
        except Exception as exc:  # noqa: BLE001
            print(f"[MNEMOS] Semantic retrieval failed ({exc}) — falling back to DirectRetrieval", flush=True)
            return await self._fallback.retrieve_context(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids, diagram_ids=diagram_ids,
            )

    async def _semantic_retrieve(
        self,
        db: DatabasePort,
        question: str,
        set_ids: list[str],
        *,
        max_tokens: int = 8000,
        package_ids: list[str] | None = None,
        diagram_ids: list[str] | None = None,
    ) -> str:
        """Query MNEMOS for semantically relevant architecture engrams."""
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

        # Build ChromaDB metadata filters to scope to architecture data
        # and requested sets. Engram metadata keys are prefixed with "app_"
        # in ChromaDB (see chromadb_tier.py line 74).
        arch_type_filter: dict[str, object] = {
            "app_iris_type": {"$in": ["element", "relationship", "diagram"]},
        }

        if len(set_ids) == 1:
            filters: dict[str, object] = {
                "$and": [
                    arch_type_filter,
                    {"app_set_id": set_ids[0]},
                ],
            }
        elif set_ids:
            filters = {
                "$and": [
                    arch_type_filter,
                    {"app_set_id": {"$in": set_ids}},
                ],
            }
        else:
            filters = arch_type_filter

        hits = client.search(
            question,
            top_k=self._max_results,
            filters=filters,
        )

        if not hits:
            # No results — fall back to direct
            return await self._fallback.retrieve_context(
                db, question, set_ids,
                max_tokens=max_tokens, package_ids=package_ids, diagram_ids=diagram_ids,
            )

        # Build set name headers for context identity
        set_names: list[str] = []
        for sid in set_ids:
            cursor = await db.execute(
                "SELECT name, description FROM sets WHERE id = ?", (sid,),
            )
            row = await cursor.fetchone()
            if row:
                name_str = str(row[0])
                if row[1]:
                    name_str += f": {row[1]}"
                set_names.append(name_str)

        # Format hits as structured text with set headers
        header_parts = [f"SEMANTIC CONTEXT ({len(hits)} results):"]
        for sn in set_names:
            header_parts.append(f"Set: {sn}")
        header = "\n".join(header_parts) + "\n\n"

        lines: list[str] = []
        for hit in hits:
            engram = hit.engram if hasattr(hit, "engram") else hit
            content = engram.get("content", "") if isinstance(engram, dict) else str(engram)
            score = hit.score if hasattr(hit, "score") else 0.0
            lines.append(f"- [{score:.2f}] {content}")

        return header + "\n".join(lines)


async def create_semantic_retrieval(db: DatabasePort) -> RetrievalPort:
    """Create a SemanticRetrieval instance from extension config."""
    config = await _get_mnemos_config(db)
    url = str(config.get("url", _DEFAULT_URL))
    timeout_ms = int(config.get("timeout_ms", _DEFAULT_TIMEOUT_MS))
    max_results = int(config.get("max_results", _DEFAULT_MAX_RESULTS))
    return SemanticRetrieval(url, timeout_ms, max_results)


async def search_docref_semantic(
    db: DatabasePort,
    question: str,
    document_ids: list[str],
    *,
    max_results: int = 50,
    max_tokens: int = 4000,
) -> str | None:
    """Search MNEMOS for DocRef legislation chunks relevant to the question.

    Uses metadata filtering to scope results to docref_chunk engrams from
    the selected documents only. Returns formatted context string, or None
    if MNEMOS is unavailable (caller should fall back to direct DB reads).
    """
    try:
        from mnemos_sdk import MnemosClient, MnemosConfig  # type: ignore[import-untyped]
    except ImportError:
        return None

    config = await _get_mnemos_config(db)
    url = str(config.get("url", _DEFAULT_URL))
    timeout_ms = int(config.get("timeout_ms", _DEFAULT_TIMEOUT_MS))

    sdk_config = MnemosConfig(base_url=url, timeout_s=timeout_ms / 1000)
    client = MnemosClient(sdk_config)

    # Build filters: docref_chunk type AND matching document_ids
    if len(document_ids) == 1:
        filters: dict[str, object] = {
            "$and": [
                {"app_iris_type": "docref_chunk"},
                {"app_document_id": document_ids[0]},
            ],
        }
    else:
        filters = {
            "$and": [
                {"app_iris_type": "docref_chunk"},
                {"app_document_id": {"$in": document_ids}},
            ],
        }

    try:
        hits = client.search(question, top_k=max_results, filters=filters)
    except Exception:  # noqa: BLE001
        log.warning("MNEMOS docref search failed", exc_info=True)
        return None

    if not hits:
        return None

    # Build document title lookup from engram metadata
    doc_titles: dict[str, str] = {}
    for hit in hits:
        engram = hit.engram if hasattr(hit, "engram") else hit
        metadata = engram.get("metadata", {}) if isinstance(engram, dict) else {}
        did = metadata.get("document_id", "")
        dtitle = metadata.get("document_title", "")
        if did and dtitle and did not in doc_titles:
            doc_titles[did] = dtitle

    # Format hits as structured text with document headers and token budget
    max_chars = max_tokens * _CHARS_PER_TOKEN

    # Build header listing the documents
    header_parts = [f"LEGISLATION (semantic, {len(hits)} results):"]
    for did, dtitle in doc_titles.items():
        header_parts.append(f"Source: {dtitle}")
    header = "\n".join(header_parts) + "\n\n"

    lines: list[str] = []
    char_count = len(header)
    for hit in hits:
        engram = hit.engram if hasattr(hit, "engram") else hit
        content = engram.get("content", "") if isinstance(engram, dict) else str(engram)
        score = hit.score if hasattr(hit, "score") else 0.0
        line = f"- [{score:.2f}] {content}"
        if char_count + len(line) > max_chars:
            break
        lines.append(line)
        char_count += len(line)

    if not lines:
        return None

    print(f"[MNEMOS] DocRef semantic: {len(lines)} hits for {len(document_ids)} docs", flush=True)
    return header + "\n".join(lines)


async def check_mnemos_health(url: str) -> bool:
    """Check if MNEMOS service is healthy at the given URL."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            return resp.status_code == 200  # noqa: PLR2004
    except Exception:  # noqa: BLE001
        return False
