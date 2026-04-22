"""Shared pytest fixtures for iris-client tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx

from iris_client import IrisClient


@pytest.fixture
def respx_mock() -> respx.Router:
    """Active `respx` router that intercepts httpx requests."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
async def anon_client() -> AsyncIterator[IrisClient]:
    """Anonymous client pointed at a fixed base URL (no IRIS_TOKEN)."""
    async with IrisClient(url="http://iris.test", token=None) as client:
        yield client


@pytest.fixture
async def pat_client() -> AsyncIterator[IrisClient]:
    """Client authenticated with a fake PAT."""
    async with IrisClient(url="http://iris.test", token="iris_pat_abc12345_fakefakefake") as client:
        yield client
