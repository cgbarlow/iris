"""Retrieval strategy abstraction for AI context building (ADR-111).

Defines RetrievalPort protocol and implementations:
- DirectRetrieval: wraps existing context.py (default, always available)
- SemanticRetrieval: uses MNEMOS for semantic search (when extension enabled)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.ai.context import build_multi_set_context, build_set_context

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

log = logging.getLogger("app.ai.retrieval")


@runtime_checkable
class RetrievalPort(Protocol):
    """Protocol for retrieving AI context from architecture data."""

    async def retrieve_context(
        self,
        db: DatabasePort,
        question: str,
        set_ids: list[str],
        *,
        max_tokens: int = 8000,
        package_ids: list[str] | None = None,
    ) -> str:
        """Retrieve context for an AI question. Returns structured text."""
        ...


class DirectRetrieval:
    """Retrieves context via direct database queries (existing context.py logic).

    This is the default strategy — always available, no external dependencies.
    """

    async def retrieve_context(
        self,
        db: DatabasePort,
        question: str,
        set_ids: list[str],
        *,
        max_tokens: int = 8000,
        package_ids: list[str] | None = None,
    ) -> str:
        """Build context by querying the database directly."""
        if len(set_ids) == 1:
            return await build_set_context(
                db, set_ids[0], max_tokens=max_tokens, package_ids=package_ids,
            )
        return await build_multi_set_context(
            db, set_ids, max_tokens=max_tokens, package_ids=package_ids,
        )


async def get_retrieval_strategy(db: DatabasePort) -> RetrievalPort:
    """Resolve the active retrieval strategy based on extension state.

    Returns SemanticRetrieval if the MNEMOS extension is installed and enabled,
    otherwise returns DirectRetrieval.
    """
    try:
        from app.extensions.service import is_extension_enabled

        if await is_extension_enabled(db, "mnemos"):
            from app.mnemos.setup import ensure_sdk_importable

            ensure_sdk_importable()

            from app.mnemos.adapter import create_semantic_retrieval

            strategy = await create_semantic_retrieval(db)
            print("[MNEMOS] Extension enabled — using SemanticRetrieval", flush=True)
            return strategy
    except Exception:  # noqa: BLE001
        print("[MNEMOS] Extension check failed — falling back to DirectRetrieval", flush=True)
    print("[MNEMOS] Extension not enabled — using DirectRetrieval", flush=True)
    return DirectRetrieval()
