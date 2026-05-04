"""Shared fixtures for iris-mcp tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from iris_client import IrisClient


@pytest.fixture
def respx_mock() -> respx.Router:
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
async def client() -> AsyncIterator[IrisClient]:
    async with IrisClient(url="http://iris.test", token="iris_pat_test_fake") as c:
        yield c
