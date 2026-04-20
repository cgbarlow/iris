"""AI client abstraction — provider-agnostic LLM interface (ADR-093).

Translated from machine-dream_ag's LMStudioClient.ts, LLMClientFactory.ts,
ValidatedLLMClient.ts patterns: ABC, OpenAI-compatible client, Anthropic client,
retry on network/5xx errors (not on timeouts or 4xx auth).
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx

from app.ai.models import ProviderTestResult

if TYPE_CHECKING:
    pass


# Default base URLs per provider type
_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
    # anthropic is handled separately — not an OpenAI-compat endpoint
}

_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"


def _is_retryable(exc: Exception) -> bool:
    """Translated from machine-dream's isRetryableError: retry on network/5xx, not timeout/4xx."""
    if isinstance(exc, httpx.TimeoutException):
        return False
    if isinstance(exc, (httpx.NetworkError, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500  # noqa: PLR2004
    return False


async def _with_retry(
    coro_fn: object,
    retries: int,
    *args: object,
    **kwargs: object,
) -> object:
    """Call coro_fn with exponential backoff retry on retryable errors."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await coro_fn(*args, **kwargs)  # type: ignore[operator]
        except Exception as exc:  # noqa: BLE001
            if not _is_retryable(exc) or attempt == retries:
                raise
            last_exc = exc
            await asyncio.sleep(2 ** attempt)
    # Should not reach here, but satisfy type checker
    raise last_exc or RuntimeError("Retry failed")  # type: ignore[misc]


class AIClient(ABC):
    """Abstract base for LLM provider clients."""

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> tuple[str, int | None, int | None]:
        """Send messages and return (answer, tokens_in, tokens_out)."""

    @abstractmethod
    async def chat_stream(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        """Stream response chunks as strings."""
        # Make mypy happy — subclasses use 'yield'
        raise NotImplementedError
        yield  # pragma: no cover

    @abstractmethod
    async def test_connection(self) -> ProviderTestResult:
        """Test provider connectivity. Returns result with latency or error."""


class OpenAICompatibleClient(AIClient):
    """Client for OpenAI-compatible endpoints: openai, ollama, lmstudio, openrouter, custom."""

    def __init__(self, provider_row: dict[str, object]) -> None:
        self._provider = provider_row
        provider_type = str(provider_row["provider_type"])
        base_url = (
            str(provider_row["base_url"])
            if provider_row.get("base_url")
            else _DEFAULT_BASE_URLS.get(provider_type, "http://localhost:1234/v1")
        )
        self._base_url = base_url.rstrip("/")
        self._model = str(provider_row["model"])
        self._timeout = (int(provider_row["timeout_ms"]) if provider_row.get("timeout_ms") else 30000) / 1000.0  # noqa: E501
        self._retries = int(provider_row["retries"]) if provider_row.get("retries") else 3
        import json
        params_raw = provider_row.get("parameters") or "{}"
        self._params: dict[str, object] = json.loads(str(params_raw)) if isinstance(params_raw, str) else {}
        self._api_key: str | None = str(provider_row["api_key"]) if provider_row.get("api_key") else None
        self.stream_usage: tuple[int | None, int | None] = (None, None)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def _payload(self, messages: list[dict[str, str]], *, stream: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
        }
        if stream:
            payload["stream_options"] = {"include_usage": True}
        if self._params.get("temperature") is not None:
            payload["temperature"] = self._params["temperature"]
        if self._params.get("max_tokens") is not None:
            payload["max_tokens"] = self._params["max_tokens"]
        if self._params.get("top_p") is not None:
            payload["top_p"] = self._params["top_p"]
        if self._params.get("top_k") is not None:
            payload["top_k"] = self._params["top_k"]
        if self._params.get("min_p") is not None:
            payload["min_p"] = self._params["min_p"]
        if self._params.get("frequency_penalty") is not None:
            payload["frequency_penalty"] = self._params["frequency_penalty"]
        if self._params.get("presence_penalty") is not None:
            payload["presence_penalty"] = self._params["presence_penalty"]
        if self._params.get("stop") is not None:
            payload["stop"] = self._params["stop"]
        return payload

    async def _do_chat(self, messages: list[dict[str, str]]) -> tuple[str, int | None, int | None]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages),
            )
            resp.raise_for_status()
            data = resp.json()
            answer: str = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens_in: int | None = usage.get("prompt_tokens")
            tokens_out: int | None = usage.get("completion_tokens")
            return answer, tokens_in, tokens_out

    async def chat(self, messages: list[dict[str, str]]) -> tuple[str, int | None, int | None]:
        return await _with_retry(self._do_chat, self._retries, messages)  # type: ignore[return-value]

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.stream_usage = (None, None)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, stream=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(payload)
                        usage = chunk.get("usage")
                        if usage:
                            self.stream_usage = (usage.get("prompt_tokens"), usage.get("completion_tokens"))
                        choices = chunk.get("choices") or []
                        if choices:
                            content = choices[0].get("delta", {}).get("content")
                            if content:
                                yield content
                    except (KeyError, ValueError, IndexError):
                        continue

    async def test_connection(self) -> ProviderTestResult:
        start = time.monotonic()
        try:
            answer, _, _ = await self._do_chat([{"role": "user", "content": "Say 'ok'"}])
            latency = int((time.monotonic() - start) * 1000)
            return ProviderTestResult(ok=True, latency_ms=latency)
        except Exception as exc:  # noqa: BLE001
            return ProviderTestResult(ok=False, error=str(exc))


class AnthropicClient(AIClient):
    """Client for the Anthropic Messages API (/v1/messages)."""

    def __init__(self, provider_row: dict[str, object]) -> None:
        self._provider = provider_row
        base_url = (
            str(provider_row["base_url"])
            if provider_row.get("base_url")
            else _ANTHROPIC_BASE_URL
        )
        self._base_url = base_url.rstrip("/")
        self._model = str(provider_row["model"])
        self._timeout = (int(provider_row["timeout_ms"]) if provider_row.get("timeout_ms") else 30000) / 1000.0  # noqa: E501
        self._retries = int(provider_row["retries"]) if provider_row.get("retries") else 3
        import json
        params_raw = provider_row.get("parameters") or "{}"
        self._params: dict[str, object] = json.loads(str(params_raw)) if isinstance(params_raw, str) else {}
        self._api_key: str | None = str(provider_row["api_key"]) if provider_row.get("api_key") else None
        self._system_prompt: str | None = str(provider_row["system_prompt"]) if provider_row.get("system_prompt") else None  # noqa: E501
        self.stream_usage: tuple[int | None, int | None] = (None, None)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": _ANTHROPIC_VERSION,
        }
        if self._api_key:
            h["x-api-key"] = self._api_key
        return h

    def _payload(self, messages: list[dict[str, str]], *, stream: bool = False) -> dict[str, object]:
        # Anthropic: system is a top-level param, not a message
        user_messages = [m for m in messages if m["role"] != "system"]
        payload: dict[str, object] = {
            "model": self._model,
            "messages": user_messages,
            "max_tokens": self._params.get("max_tokens") or 4096,
            "stream": stream,
        }
        # System prompt: from provider config OR from messages
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system = "\n\n".join(system_parts) if system_parts else self._system_prompt
        if system:
            payload["system"] = system
        if self._params.get("temperature") is not None:
            payload["temperature"] = self._params["temperature"]
        if self._params.get("top_p") is not None:
            payload["top_p"] = self._params["top_p"]
        if self._params.get("top_k") is not None:
            payload["top_k"] = self._params["top_k"]
        if self._params.get("stop") is not None:
            payload["stop_sequences"] = self._params["stop"]
        return payload

    async def _do_chat(self, messages: list[dict[str, str]]) -> tuple[str, int | None, int | None]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=self._payload(messages),
            )
            resp.raise_for_status()
            data = resp.json()
            answer: str = data["content"][0]["text"]
            usage = data.get("usage", {})
            tokens_in: int | None = usage.get("input_tokens")
            tokens_out: int | None = usage.get("output_tokens")
            return answer, tokens_in, tokens_out

    async def chat(self, messages: list[dict[str, str]]) -> tuple[str, int | None, int | None]:
        return await _with_retry(self._do_chat, self._retries, messages)  # type: ignore[return-value]

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.stream_usage = (None, None)
        tokens_in: int | None = None
        tokens_out: int | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=self._payload(messages, stream=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    import json
                    try:
                        event = json.loads(line[6:])
                        etype = event.get("type")
                        if etype == "message_start":
                            usage = event.get("message", {}).get("usage", {})
                            tokens_in = usage.get("input_tokens")
                        elif etype == "message_delta":
                            usage = event.get("usage", {})
                            tokens_out = usage.get("output_tokens")
                        elif etype == "content_block_delta":
                            text = event.get("delta", {}).get("text")
                            if text:
                                yield text
                    except (KeyError, ValueError):
                        continue
        self.stream_usage = (tokens_in, tokens_out)

    async def test_connection(self) -> ProviderTestResult:
        start = time.monotonic()
        try:
            answer, _, _ = await self._do_chat([{"role": "user", "content": "Say 'ok'"}])
            latency = int((time.monotonic() - start) * 1000)
            return ProviderTestResult(ok=True, latency_ms=latency)
        except Exception as exc:  # noqa: BLE001
            return ProviderTestResult(ok=False, error=str(exc))


def create_ai_client(provider_row: dict[str, object]) -> AIClient:
    """Factory: select client implementation by provider_type."""
    if provider_row.get("provider_type") == "anthropic":
        return AnthropicClient(provider_row)
    return OpenAICompatibleClient(provider_row)
