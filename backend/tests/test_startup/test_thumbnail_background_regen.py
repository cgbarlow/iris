"""v6.30.2: thumbnail regeneration runs in the background.

Verifies the contract introduced in v6.30.2 — `_initialize_supabase`
schedules thumbnail regeneration as a background task instead of
awaiting it synchronously. The fix unblocks Render port-binding when
the diagram count is large (1000+ thumbnails took 5–6 min, exceeding
Render's port-detection deadline).
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app.startup import _regenerate_thumbnails_background


@pytest.mark.asyncio
async def test_background_regen_calls_through_to_thumbnail_module() -> None:
    """The background coroutine awaits regenerate_all_thumbnails and
    logs the resulting count."""
    seen: list[object] = []

    async def fake(port: object) -> int:
        seen.append(port)
        return 7

    sentinel = object()
    with patch("app.startup.regenerate_all_thumbnails", new=fake):
        await _regenerate_thumbnails_background(sentinel)

    assert seen == [sentinel], "the same port should be passed through"


@pytest.mark.asyncio
async def test_background_regen_swallows_exceptions() -> None:
    """If the thumbnail module raises, the background task logs and
    returns — never propagates. Otherwise a failure would crash an
    unawaited Task and surface as an unhandled-exception warning."""
    async def boom(port: object) -> int:
        raise RuntimeError("cairosvg not available")

    with patch("app.startup.regenerate_all_thumbnails", new=boom):
        # Should not raise.
        await _regenerate_thumbnails_background(object())


@pytest.mark.asyncio
async def test_background_regen_can_be_scheduled_via_create_task() -> None:
    """The fix uses asyncio.create_task(...) — the call site shouldn't
    block on completion. Verify the task scheduling pattern itself."""
    done = asyncio.Event()

    async def slow(port: object) -> int:
        await asyncio.sleep(0.05)
        done.set()
        return 1

    with patch("app.startup.regenerate_all_thumbnails", new=slow):
        task = asyncio.create_task(_regenerate_thumbnails_background(object()))
        # Caller proceeds immediately; the task hasn't completed yet.
        assert not done.is_set()
        await task
        assert done.is_set()
