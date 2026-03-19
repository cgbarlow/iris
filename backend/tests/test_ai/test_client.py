"""Tests for AI client abstraction with mocked HTTP (ADR-093)."""

import json

import httpx
import pytest

from app.ai.client import (
    AnthropicClient,
    OpenAICompatibleClient,
    create_ai_client,
    _is_retryable,
)
from app.ai.models import ProviderTestResult


def make_provider(provider_type="openai", model="gpt-4o", **kwargs):
    return {
        "id": "test-id",
        "name": "Test",
        "provider_type": provider_type,
        "base_url": None,
        "api_key_env_var": None,
        "model": model,
        "parameters": "{}",
        "system_prompt": None,
        "timeout_ms": 5000,
        "retries": 0,  # No retries in tests
        **kwargs,
    }


class TestIsRetryable:
    def test_network_error_retryable(self):
        assert _is_retryable(httpx.NetworkError("conn failed"))

    def test_connect_error_retryable(self):
        assert _is_retryable(httpx.ConnectError("refused"))

    def test_timeout_not_retryable(self):
        assert not _is_retryable(httpx.TimeoutException("timeout"))

    def test_4xx_not_retryable(self):
        resp = httpx.Response(401)
        exc = httpx.HTTPStatusError("auth", request=httpx.Request("POST", "http://x"), response=resp)
        assert not _is_retryable(exc)

    def test_5xx_retryable(self):
        resp = httpx.Response(503)
        exc = httpx.HTTPStatusError("srv err", request=httpx.Request("POST", "http://x"), response=resp)
        assert _is_retryable(exc)

    def test_429_retryable(self):
        resp = httpx.Response(429)
        exc = httpx.HTTPStatusError("rate limit", request=httpx.Request("POST", "http://x"), response=resp)
        assert _is_retryable(exc)


class TestOpenAICompatibleClient:
    def _make_chat_response(self, content: str, tokens_in=10, tokens_out=20):
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out},
        }

    @pytest.mark.asyncio
    async def test_chat_success(self, respx_mock):
        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=self._make_chat_response("Hello!"))
        )
        client = OpenAICompatibleClient(make_provider())
        answer, tokens_in, tokens_out = await client.chat([{"role": "user", "content": "Hi"}])
        assert answer == "Hello!"
        assert tokens_in == 10
        assert tokens_out == 20

    @pytest.mark.asyncio
    async def test_chat_with_api_key(self, respx_mock, monkeypatch):
        monkeypatch.setenv("MY_KEY", "sk-test123")
        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=self._make_chat_response("ok"))
        )
        provider = make_provider(api_key_env_var="MY_KEY")
        client = OpenAICompatibleClient(provider)
        answer, _, _ = await client.chat([{"role": "user", "content": "ping"}])
        assert answer == "ok"

    @pytest.mark.asyncio
    async def test_test_connection_ok(self, respx_mock):
        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=self._make_chat_response("ok"))
        )
        client = OpenAICompatibleClient(make_provider())
        result = await client.test_connection()
        assert result.ok is True
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, respx_mock):
        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(500)
        )
        client = OpenAICompatibleClient(make_provider())
        result = await client.test_connection()
        assert result.ok is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_custom_base_url(self, respx_mock):
        respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=self._make_chat_response("ollama says hi"))
        )
        provider = make_provider(provider_type="ollama", base_url="http://localhost:11434/v1")
        client = OpenAICompatibleClient(provider)
        answer, _, _ = await client.chat([{"role": "user", "content": "hi"}])
        assert answer == "ollama says hi"


class TestAnthropicClient:
    def _make_messages_response(self, content: str, tokens_in=15, tokens_out=30):
        return {
            "content": [{"type": "text", "text": content}],
            "usage": {"input_tokens": tokens_in, "output_tokens": tokens_out},
        }

    @pytest.mark.asyncio
    async def test_chat_success(self, respx_mock):
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=self._make_messages_response("Claude here"))
        )
        provider = make_provider(provider_type="anthropic", model="claude-3-5-sonnet-20241022")
        client = AnthropicClient(provider)
        answer, tokens_in, tokens_out = await client.chat([{"role": "user", "content": "Hello"}])
        assert answer == "Claude here"
        assert tokens_in == 15
        assert tokens_out == 30

    @pytest.mark.asyncio
    async def test_system_prompt_from_messages(self, respx_mock):
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=self._make_messages_response("ok"))
        )
        provider = make_provider(provider_type="anthropic", model="claude-3-5-sonnet-20241022")
        client = AnthropicClient(provider)
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hi"},
        ]
        answer, _, _ = await client.chat(messages)
        assert answer == "ok"

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, respx_mock):
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(401)
        )
        provider = make_provider(provider_type="anthropic", model="claude-3-5-sonnet-20241022")
        client = AnthropicClient(provider)
        result = await client.test_connection()
        assert result.ok is False


class TestFactory:
    def test_creates_openai_client(self):
        client = create_ai_client(make_provider(provider_type="openai"))
        assert isinstance(client, OpenAICompatibleClient)

    def test_creates_anthropic_client(self):
        client = create_ai_client(make_provider(provider_type="anthropic"))
        assert isinstance(client, AnthropicClient)

    def test_creates_ollama_client(self):
        client = create_ai_client(make_provider(provider_type="ollama"))
        assert isinstance(client, OpenAICompatibleClient)

    def test_creates_lmstudio_client(self):
        client = create_ai_client(make_provider(provider_type="lmstudio"))
        assert isinstance(client, OpenAICompatibleClient)
