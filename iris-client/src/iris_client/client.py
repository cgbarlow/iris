"""`IrisClient` — the single async HTTP client shared by iris-cli and iris-mcp.

Typed async methods for the v1 iris surface (read-only + AI per
ADR-127/128/129/130/131/132). Each method wraps one HTTP endpoint and
returns either a Pydantic model from ``iris_client.models.core`` or
``bytes`` for binary exports / thumbnails.

See ADR-132 and SPEC-132-A.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from types import TracebackType
from typing import Any, Literal

import httpx

from iris_client.auth import bearer_headers
from iris_client.exceptions import from_httpx_error
from iris_client.models.core import (
    ApplyCreationResponse,
    Collection,
    Conversation,
    Diagram,
    Element,
    FileContext,
    FileExtractResponse,
    IrisSet,
    LoginResponse,
    Package,
    PackageHierarchyNode,
    QAResponse,
    ResponseFormatType,
    ResponsePromptComposed,
    ScopePromptIndexEntry,
    SearchResponse,
    TokenCreated,
    TokenRecord,
    UserSelf,
    Version,
)
from iris_client.streaming import AskStreamEvent, iter_sse_events

DEFAULT_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = "iris-client/0.1"

ExportFormat = Literal["json", "markdown"]


class IrisClient:
    """Async HTTP client for the Iris API.

    Resolves `url` and `token` from:
      1. constructor arguments
      2. environment (`IRIS_URL`, `IRIS_TOKEN`)
      3. defaults (`http://localhost:8000`, anonymous)

    Use as an async context manager::

        async with IrisClient(token="iris_pat_...") as client:
            hits = await client.search("payment")
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
        self.token: str | None = (
            token if token is not None else os.environ.get("IRIS_TOKEN")
        )
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

    # v6.0.0 (ADR-164): set_token removed. The HTTP transport gets the
    # bearer from request headers per-request; the stdio transport sets
    # it once at IrisClient construction from IRIS_TOKEN env var.

    # --- Private helpers -----------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method, path,
                params=dict(params) if params else None,
                json=json,
                data=data,
                files=files,
                headers=dict(headers) if headers else None,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise from_httpx_error(exc) from exc
        return response

    # --- Auth ----------------------------------------------------------------

    async def login(self, username: str, password: str) -> LoginResponse:
        """Exchange username+password for a JWT. Used by `iris login` to then mint a PAT."""
        response = await self._request(
            "POST", "/api/auth/login", json={"username": username, "password": password},
        )
        return LoginResponse.model_validate(response.json())

    async def whoami(self) -> UserSelf:
        response = await self._request("GET", "/api/auth/me")
        return UserSelf.model_validate(response.json())

    async def create_token(
        self, name: str, *, expires_at: str | None = None,
    ) -> TokenCreated:
        body: dict[str, Any] = {"name": name}
        if expires_at is not None:
            body["expires_at"] = expires_at
        response = await self._request(
            "POST", "/api/users/me/tokens", json=body,
        )
        return TokenCreated.model_validate(response.json())

    async def list_tokens(self) -> list[TokenRecord]:
        response = await self._request("GET", "/api/users/me/tokens")
        return [TokenRecord.model_validate(r) for r in response.json()]

    async def revoke_token(self, token_id: str) -> None:
        await self._request("DELETE", f"/api/users/me/tokens/{token_id}")

    # v6.0.0 (ADR-164): pairing-code methods (create_pairing_code,
    # exchange_pairing_code) removed. OAuth replaces the pairing flow.

    # --- Search --------------------------------------------------------------

    async def search(
        self,
        q: str,
        *,
        set_id: str | None = None,
        collection_id: str | None = None,
        limit: int = 50,
    ) -> SearchResponse:
        params: dict[str, Any] = {"q": q, "limit": limit}
        if set_id:
            params["set_id"] = set_id
        if collection_id:
            params["collection_id"] = collection_id
        response = await self._request("GET", "/api/search", params=params)
        return SearchResponse.model_validate(response.json())

    # --- Diagrams ------------------------------------------------------------

    async def list_diagrams(
        self,
        *,
        set_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Diagram]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if set_id:
            params["set_id"] = set_id
        response = await self._request("GET", "/api/diagrams", params=params)
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [Diagram.model_validate(r) for r in items]

    async def get_diagram(self, diagram_id: str) -> Diagram:
        response = await self._request("GET", f"/api/diagrams/{diagram_id}")
        return Diagram.model_validate(response.json())

    async def get_diagram_versions(self, diagram_id: str) -> list[Version]:
        response = await self._request("GET", f"/api/diagrams/{diagram_id}/versions")
        return [Version.model_validate(r) for r in response.json()]

    async def get_diagram_thumbnail(
        self, diagram_id: str, *, theme: str = "light",
    ) -> bytes:
        response = await self._request(
            "GET", f"/api/diagrams/{diagram_id}/thumbnail", params={"theme": theme},
        )
        return response.content

    # --- Elements ------------------------------------------------------------

    async def list_elements(
        self,
        *,
        set_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Element]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if set_id:
            params["set_id"] = set_id
        response = await self._request("GET", "/api/elements", params=params)
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [Element.model_validate(r) for r in items]

    async def get_element(self, element_id: str) -> Element:
        response = await self._request("GET", f"/api/elements/{element_id}")
        return Element.model_validate(response.json())

    async def get_element_versions(self, element_id: str) -> list[Version]:
        response = await self._request("GET", f"/api/elements/{element_id}/versions")
        return [Version.model_validate(r) for r in response.json()]

    # --- Packages ------------------------------------------------------------

    async def list_packages(
        self,
        *,
        set_id: str | None = None,
        collection_id: str | None = None,
        parent_package_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Package]:
        """List packages. ADR-158 (v5.13.0): supports pagination
        (`page`, `page_size`) and `parent_package_id` filter so callers
        can walk the tree level-by-level (`parent_package_id=None` for
        roots, or a specific package ID for its direct children).

        The backend defaults to `page_size=50, max 100`. For a full
        structural overview, prefer `package_hierarchy()` — one call
        returns the entire tree.
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if set_id:
            params["set_id"] = set_id
        if collection_id:
            params["collection_id"] = collection_id
        if parent_package_id is not None:
            params["parent_package_id"] = parent_package_id
        response = await self._request("GET", "/api/packages", params=params)
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [Package.model_validate(r) for r in items]

    async def get_package(self, package_id: str) -> Package:
        response = await self._request("GET", f"/api/packages/{package_id}")
        return Package.model_validate(response.json())

    async def package_hierarchy(
        self, *, set_id: str | None = None, root_id: str | None = None,
    ) -> list[PackageHierarchyNode]:
        """Return the complete package hierarchy for a set as a nested
        tree (ADR-158, v5.13.0). Each node carries `id`, `name`,
        `parent_package_id`, and `children`. Use this for structural
        overview instead of paginating `list_packages` repeatedly.
        """
        params: dict[str, Any] = {}
        if set_id:
            params["set_id"] = set_id
        if root_id:
            params["root_id"] = root_id
        response = await self._request(
            "GET", "/api/packages/hierarchy", params=params,
        )
        payload = response.json()
        # Endpoint returns a list of root nodes (each with nested children).
        return [PackageHierarchyNode.model_validate(node) for node in payload]

    async def diagram_hierarchy(
        self, *, set_id: str | None = None, root_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the diagram hierarchy (NOT the package hierarchy).
        Hits `/api/diagrams/hierarchy`. Renamed in v5.13.0 from the
        misnamed `package_hierarchy`; previously had no callers so the
        rename is non-breaking."""
        params: dict[str, Any] = {}
        if set_id:
            params["set_id"] = set_id
        if root_id:
            params["root_id"] = root_id
        response = await self._request(
            "GET", "/api/diagrams/hierarchy", params=params,
        )
        payload: dict[str, Any] = response.json()
        return payload

    # --- Sets / Collections --------------------------------------------------

    async def list_sets(
        self, *, collection_id: str | None = None,
    ) -> list[IrisSet]:
        params: dict[str, Any] = {}
        if collection_id:
            params["collection_id"] = collection_id
        response = await self._request("GET", "/api/sets", params=params)
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [IrisSet.model_validate(r) for r in items]

    async def get_set(self, set_id: str) -> IrisSet:
        response = await self._request("GET", f"/api/sets/{set_id}")
        return IrisSet.model_validate(response.json())

    async def list_collections(self) -> list[Collection]:
        response = await self._request("GET", "/api/collections")
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [Collection.model_validate(r) for r in items]

    async def get_collection(self, collection_id: str) -> Collection:
        response = await self._request("GET", f"/api/collections/{collection_id}")
        return Collection.model_validate(response.json())

    # --- Entity creation (ADR-161, v5.16.0) ---------------------------------

    async def create_collection(
        self, name: str, *, description: str | None = None,
    ) -> Collection:
        """Create a new top-level Collection. Auth required.

        Backend POST /api/collections (CollectionCreate). The
        permissive Collection model accepts the returned payload.
        """
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        response = await self._request("POST", "/api/collections", json=body)
        return Collection.model_validate(response.json())

    async def create_set(
        self,
        name: str,
        *,
        collection_id: str | None = None,
        description: str | None = None,
    ) -> IrisSet:
        """Create a new Set. Auth required.

        Pass `collection_id=None` for a top-level (uncollected) set,
        or a collection's id to nest the set inside it.
        """
        body: dict[str, Any] = {"name": name}
        if collection_id is not None:
            body["collection_id"] = collection_id
        if description is not None:
            body["description"] = description
        response = await self._request("POST", "/api/sets", json=body)
        return IrisSet.model_validate(response.json())

    async def create_package(
        self,
        name: str,
        *,
        set_id: str | None = None,
        parent_package_id: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Package:
        """Create a new Package. Auth required.

        A package is a folder inside a set. Pass `set_id=` to anchor
        the package; pass `parent_package_id=` to nest it under
        another package; omit both for a free-standing root package.
        """
        body: dict[str, Any] = {"name": name}
        if set_id is not None:
            body["set_id"] = set_id
        if parent_package_id is not None:
            body["parent_package_id"] = parent_package_id
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        response = await self._request("POST", "/api/packages", json=body)
        return Package.model_validate(response.json())

    # --- Scope prompts (ADR-152) --------------------------------------------

    async def list_scope_prompts(self) -> list[ScopePromptIndexEntry]:
        """Return one entry per Collection / Set with a non-empty system_prompt."""
        response = await self._request("GET", "/api/prompts/scope-index")
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [ScopePromptIndexEntry.model_validate(r) for r in items]

    # --- Response-format prompts (ADR-157, v5.12.0) -------------------------

    async def list_response_format_types(
        self, *, purpose: str = "response_format",
    ) -> list["ResponseFormatType"]:
        """List distinct (notation, diagram_type) pairs that have at least
        one active prompt of the requested purpose. Anonymous-readable.

        `purpose` defaults to ``response_format`` (backwards-compatible).
        Pass ``creation_format`` to discover diagram-creation-capable
        pairs (ADR-162, v5.17.0)."""
        response = await self._request(
            "GET", "/api/ai/response-prompts/types",
            params={"purpose": purpose},
        )
        return [ResponseFormatType.model_validate(r) for r in response.json()]

    async def get_response_prompt(
        self,
        notation: str,
        diagram_type: str | None = None,
        *,
        purpose: str = "response_format",
    ) -> "ResponsePromptComposed":
        """Fetch the composed prompt cascade for a (notation,
        diagram_type) pair. Anonymous-readable. Returns the composed body
        as the `body` field; empty string if no rows match.

        `purpose` defaults to ``response_format`` for backwards
        compatibility. Pass ``creation_format`` to get the layered
        creation cascade Iris AI uses when generating diagrams — used
        by MCP clients to drive local-AI diagram creation (ADR-162)."""
        params: dict[str, str] = {"notation": notation, "purpose": purpose}
        if diagram_type is not None:
            params["diagram_type"] = diagram_type
        response = await self._request(
            "GET", "/api/ai/response-prompts/composed", params=params,
        )
        return ResponsePromptComposed.model_validate(response.json())

    # --- Export --------------------------------------------------------------

    async def export_diagram(
        self, diagram_id: str, *, format: ExportFormat,
    ) -> bytes:
        return await self._export("diagrams", diagram_id, format)

    async def export_element(
        self, element_id: str, *, format: ExportFormat,
    ) -> bytes:
        return await self._export("elements", element_id, format)

    async def export_package(
        self, package_id: str, *, format: ExportFormat,
    ) -> bytes:
        return await self._export("packages", package_id, format)

    async def export_set(
        self, set_id: str, *, format: ExportFormat,
    ) -> bytes:
        return await self._export("sets", set_id, format)

    async def export_collection(
        self, collection_id: str, *, format: ExportFormat,
    ) -> bytes:
        return await self._export("collections", collection_id, format)

    async def _export(self, kind: str, entity_id: str, fmt: ExportFormat) -> bytes:
        response = await self._request(
            "GET", f"/api/export/{kind}/{entity_id}", params={"format": fmt},
        )
        return response.content

    # --- AI ------------------------------------------------------------------

    async def ask(
        self,
        question: str,
        *,
        set_ids: list[str] | None = None,
        collection_id: str | None = None,
        mode: str = "discuss",
        notation: str | None = None,
        thread_id: str | None = None,
        file_contexts: list[FileContext] | None = None,
        provider_id: str | None = None,
    ) -> QAResponse:
        """Non-streaming multi-set ask via POST /api/ai/ask."""
        body = self._ask_body(
            question=question,
            set_ids=set_ids,
            collection_id=collection_id,
            mode=mode,
            notation=notation,
            thread_id=thread_id,
            file_contexts=file_contexts,
            provider_id=provider_id,
        )
        response = await self._request("POST", "/api/ai/ask", json=body)
        return QAResponse.model_validate(response.json())

    async def ask_stream(
        self,
        question: str,
        *,
        set_ids: list[str] | None = None,
        collection_id: str | None = None,
        mode: str = "discuss",
        notation: str | None = None,
        thread_id: str | None = None,
        file_contexts: list[FileContext] | None = None,
        provider_id: str | None = None,
    ) -> AsyncIterator[AskStreamEvent]:
        """SSE-stream ask via POST /api/ai/ask?stream=true."""
        body = self._ask_body(
            question=question,
            set_ids=set_ids,
            collection_id=collection_id,
            mode=mode,
            notation=notation,
            thread_id=thread_id,
            file_contexts=file_contexts,
            provider_id=provider_id,
        )
        return self._stream_ask(body)

    async def _stream_ask(
        self, body: dict[str, Any],
    ) -> AsyncIterator[AskStreamEvent]:
        async with self._client.stream(
            "POST", "/api/ai/ask", params={"stream": "true"}, json=body,
        ) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise from_httpx_error(exc) from exc
            async for event in iter_sse_events(response):
                yield event

    @staticmethod
    def _ask_body(
        *,
        question: str,
        set_ids: list[str] | None,
        collection_id: str | None,
        mode: str,
        notation: str | None,
        thread_id: str | None,
        file_contexts: list[FileContext] | None,
        provider_id: str | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"question": question, "mode": mode}
        if set_ids:
            body["set_ids"] = set_ids
        if collection_id:
            body["collection_id"] = collection_id
        if notation:
            body["notation"] = notation
        if thread_id:
            body["thread_id"] = thread_id
        if provider_id:
            body["provider_id"] = provider_id
        if file_contexts:
            body["file_contexts"] = [
                fc.model_dump() if isinstance(fc, FileContext) else fc
                for fc in file_contexts
            ]
        return body

    async def extract_file_text(
        self, filename: str, content: bytes, *, content_type: str = "application/octet-stream",
    ) -> FileExtractResponse:
        files = {"file": (filename, content, content_type)}
        response = await self._request(
            "POST", "/api/ai/files/extract", files=files,
        )
        return FileExtractResponse.model_validate(response.json())

    async def create_diagram(
        self,
        *,
        diagram_type: str,
        name: str,
        notation: str | None = None,
        data: dict[str, Any] | None = None,
        set_id: str | None = None,
        parent_package_id: str | None = None,
        description: str | None = None,
    ) -> Diagram:
        """Create a new diagram (POST /api/diagrams). Auth required.

        Used by the v5.12.0 save-doview-analysis MCP tool (ADR-157) to
        persist a generated `doview_analysis` markdown document as a
        first-class Iris artefact.
        """
        body: dict[str, Any] = {
            "diagram_type": diagram_type,
            "name": name,
            "data": data or {},
        }
        if notation is not None:
            body["notation"] = notation
        if set_id is not None:
            body["set_id"] = set_id
        if parent_package_id is not None:
            body["parent_package_id"] = parent_package_id
        if description is not None:
            body["description"] = description
        response = await self._request("POST", "/api/diagrams", json=body)
        return Diagram.model_validate(response.json())

    async def apply_diagram_creation(
        self,
        set_id: str,
        diagrams_json: str,
        *,
        package_id: str | None = None,
    ) -> ApplyCreationResponse:
        body: dict[str, Any] = {"diagrams_json": diagrams_json}
        if package_id:
            body["package_id"] = package_id
        response = await self._request(
            "POST", f"/api/ai/sets/{set_id}/create-diagram/apply", json=body,
        )
        return ApplyCreationResponse.model_validate(response.json())

    async def list_conversations(
        self, set_id: str, *, limit: int = 50, offset: int = 0,
    ) -> list[Conversation]:
        response = await self._request(
            "GET", f"/api/ai/sets/{set_id}/conversations",
            params={"limit": limit, "offset": offset},
        )
        return [Conversation.model_validate(r) for r in response.json()]
