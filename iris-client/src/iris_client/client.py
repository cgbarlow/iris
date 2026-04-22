"""`IrisClient` — the single async HTTP client shared by iris-cli and iris-mcp.

Phase-2 scaffold: constructor, bearer-auth headers, async context manager,
and a `_request` helper that handles error mapping. Typed method surface
(`search`, `get_diagram`, `ask`, etc.) is filled in during Phase 6 alongside
the Pydantic models generated from the backend's OpenAPI schema.

See ADR-132 and SPEC-132-A for the full design.
"""

from __future__ import annotations

import os
from types import TracebackType
from typing import Any

import httpx

from iris_client.auth import bearer_headers
from iris_client.exceptions import from_httpx_error

DEFAULT_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = "iris-client/0.1"


class IrisClient:
    """Async HTTP client for the Iris API.

    Resolves `url` and `token` from:
      1. constructor arguments
      2. environment (`IRIS_URL`, `IRIS_TOKEN`)
      3. defaults (`http://localhost:8000`, anonymous)

    Use as an async context manager:

        async with IrisClient(token="iris_pat_...") as client:
            result = await client.whoami()
    """

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = USER_AGENT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.url: str = (url if url is not None else os.environ.get("IRIS_URL")) or DEFAULT_URL
        self.token: str | None = token if token is not None else os.environ.get("IRIS_TOKEN")
        self.user_agent = user_agent
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            **bearer_headers(self.token),
        }
        self._client = httpx.AsyncClient(
            base_url=self.url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> IrisClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def is_anonymous(self) -> bool:
        return self.token is None

    # --- Private helpers -----------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
    ) -> httpx.Response:
        """Issue a request, mapping HTTP errors onto iris exceptions.

        Non-2xx responses raise `IrisHTTPError` (or a subclass for
        401/403/429). 2xx responses are returned raw so callers can
        decode JSON, bytes, or SSE streams as appropriate.
        """
        try:
            response = await self._client.request(
                method, path, params=params, json=json, data=data, files=files,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise from_httpx_error(exc) from exc
        return response

    # --- Reference method (Phase 2) ------------------------------------------

    async def whoami(self) -> dict[str, Any]:
        """Return the authenticated user's profile.

        Reference implementation exercising the bearer-auth + request
        plumbing. Phase 6 fills in the full typed method surface and
        replaces the raw `dict` return with a Pydantic model.
        """
        response = await self._request("GET", "/api/auth/me")
        payload: dict[str, Any] = response.json()
        return payload
