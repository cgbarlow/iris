"""Regression tests for ADR-246 (trusted reverse-proxy client IP).

Behind Render (or any reverse proxy), `request.client.host` is the proxy's
own address unless the app explicitly trusts `X-Forwarded-For` from it. Both
`RateLimitMiddleware` and `AuditMiddleware` key on `request.client.host` —
so an untrusted proxy hop collapses every real caller into one shared
identity, and the anon-tier rate-limit bucket (default 30/60s) throttles
everyone together after 30 *combined* requests instead of 30 *each*.

These tests reproduce that collapse with the default config (no proxy
trusted — today's self-hosted/dev behaviour, unchanged) and confirm
`create_asgi_app` (ADR-246) fixes it once `trusted_proxy_cidrs` covers the
proxy's peer address, without weakening the limit for a single real abusive
IP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app, create_asgi_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from pathlib import Path

# A Render-like internal proxy peer — the immediate TCP connection an
# untrusted reverse proxy would present. Any non-loopback address works;
# loopback is excluded on purpose because uvicorn's own default trusted list
# (and the sliding-window key) already special-cases 127.0.0.1 in most local
# setups, which would mask the bug this test targets.
PROXY_PEER = ("10.1.2.3", 54321)


def _app_config(tmp_path: Path, *, trusted_proxy_cidrs: str = "127.0.0.1") -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
        rate_limit_anon=5,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )


async def _wrapped_client(
    config: AppConfig,
) -> tuple[httpx.AsyncClient, DatabaseManager]:
    """Build the real request path: create_app -> ProxyHeadersMiddleware,
    exactly as `create_asgi_app` does, but with the transport's peer pinned
    to PROXY_PEER and the DB wired up before the wrap (ASGITransport doesn't
    run ASGI lifespan, so tests set `.state.db_manager` directly — same
    pattern as the other rate-limit tests)."""
    inner_app = create_app(config)
    db_manager = DatabaseManager(config)
    await initialize_databases(db_manager)
    inner_app.state.db_manager = db_manager
    wrapped = ProxyHeadersMiddleware(inner_app, trusted_hosts=config.trusted_proxy_cidrs)
    transport = httpx.ASGITransport(app=wrapped, client=PROXY_PEER)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client, db_manager


class TestUntrustedProxyCollapsesCallers:
    """Default config (no proxy trusted) — today's behaviour, unchanged."""

    async def test_distinct_forwarded_ips_share_one_bucket(
        self, tmp_path: Path
    ) -> None:
        config = _app_config(tmp_path)  # trusted_proxy_cidrs defaults to 127.0.0.1
        client, db_manager = await _wrapped_client(config)
        try:
            statuses = [
                (
                    await client.get(
                        "/api/notifications/banner",
                        headers={"X-Forwarded-For": f"203.0.113.{i}"},
                    )
                ).status_code
                for i in range(1, 8)  # 7 "different" callers, limit is 5
            ]
        finally:
            await client.aclose()
            await db_manager.close()

        # Every request claimed a DIFFERENT real-world IP via X-Forwarded-For,
        # but since the proxy peer isn't trusted, the app can't tell them
        # apart — they collapse into one bucket and trip the limit together.
        assert statuses[:5] == [200] * 5
        assert statuses[5:] == [429] * 2


class TestTrustedProxyForwardsRealIp:
    """ADR-246 fix: trust the proxy's peer, honour X-Forwarded-For."""

    async def test_distinct_forwarded_ips_get_independent_buckets(
        self, tmp_path: Path
    ) -> None:
        config = _app_config(tmp_path, trusted_proxy_cidrs="10.0.0.0/8")
        client, db_manager = await _wrapped_client(config)
        try:
            # 7 distinct simulated callers, each sending only ONE request —
            # well under the limit of 5 per-IP, so all must succeed now that
            # the app can tell them apart.
            statuses = [
                (
                    await client.get(
                        "/api/notifications/banner",
                        headers={"X-Forwarded-For": f"203.0.113.{i}"},
                    )
                ).status_code
                for i in range(1, 8)
            ]
        finally:
            await client.aclose()
            await db_manager.close()

        assert statuses == [200] * 7

    async def test_single_abusive_forwarded_ip_still_throttled(
        self, tmp_path: Path
    ) -> None:
        """The fix restores per-client limiting — it doesn't remove it."""
        config = _app_config(tmp_path, trusted_proxy_cidrs="10.0.0.0/8")
        client, db_manager = await _wrapped_client(config)
        try:
            statuses = [
                (
                    await client.get(
                        "/api/notifications/banner",
                        headers={"X-Forwarded-For": "203.0.113.99"},
                    )
                ).status_code
                for _ in range(7)  # same forwarded IP every time, limit is 5
            ]
        finally:
            await client.aclose()
            await db_manager.close()

        assert statuses[:5] == [200] * 5
        assert statuses[5:] == [429] * 2


class TestCreateAsgiApp:
    """Wiring: create_asgi_app must actually apply config.trusted_proxy_cidrs."""

    def test_wraps_app_with_configured_trusted_hosts(self, tmp_path: Path) -> None:
        config = _app_config(tmp_path, trusted_proxy_cidrs="10.0.0.0/8")
        asgi_app = create_asgi_app(config)

        assert isinstance(asgi_app, ProxyHeadersMiddleware)
        assert any(
            str(net) == "10.0.0.0/8" for net in asgi_app.trusted_hosts.trusted_networks
        )

    def test_default_config_trusts_only_loopback(self, tmp_path: Path) -> None:
        config = _app_config(tmp_path)  # default trusted_proxy_cidrs
        asgi_app = create_asgi_app(config)

        assert isinstance(asgi_app, ProxyHeadersMiddleware)
        assert "10.0.0.0/8" not in str(asgi_app.trusted_hosts.trusted_networks)
