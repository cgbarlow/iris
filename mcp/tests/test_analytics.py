"""Tests for GA4 Measurement Protocol tool-call tracking (analytics.py)."""

from __future__ import annotations

import httpx

from iris_mcp import analytics

MEASUREMENT_ID = "G-TEST12345"
API_SECRET = "test-secret"


def _enable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("GA_MEASUREMENT_ID", MEASUREMENT_ID)
    monkeypatch.setenv("GA_API_SECRET", API_SECRET)


class TestIsEnabled:
    def test_disabled_when_nothing_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("GA_MEASUREMENT_ID", raising=False)
        monkeypatch.delenv("PUBLIC_GA_MEASUREMENT_ID", raising=False)
        monkeypatch.delenv("GA_API_SECRET", raising=False)
        assert analytics.is_enabled() is False

    def test_disabled_without_api_secret(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("GA_MEASUREMENT_ID", MEASUREMENT_ID)
        monkeypatch.delenv("GA_API_SECRET", raising=False)
        assert analytics.is_enabled() is False

    def test_enabled_with_both(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        _enable(monkeypatch)
        assert analytics.is_enabled() is True

    def test_falls_back_to_public_measurement_id(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        # The frontend build var doubles as the id source when the shared
        # env group only exposes PUBLIC_GA_MEASUREMENT_ID.
        monkeypatch.delenv("GA_MEASUREMENT_ID", raising=False)
        monkeypatch.setenv("PUBLIC_GA_MEASUREMENT_ID", MEASUREMENT_ID)
        monkeypatch.setenv("GA_API_SECRET", API_SECRET)
        assert analytics.is_enabled() is True


class TestBuildPayload:
    def test_shape_and_params(self) -> None:
        payload = analytics.build_payload(
            "search", success=True, duration_ms=42.7,
            client_id="cid", session_id="sid",
        )
        assert payload["client_id"] == "cid"
        events = payload["events"]
        assert isinstance(events, list) and len(events) == 1
        event = events[0]
        assert event["name"] == analytics.EVENT_NAME
        params = event["params"]
        assert params["tool"] == "search"
        assert params["success"] == "true"
        assert params["duration_ms"] == 42  # truncated to int
        assert params["session_id"] == "sid"
        assert params["engagement_time_msec"] >= 1

    def test_failure_flag(self) -> None:
        payload = analytics.build_payload("bad", success=False, duration_ms=0)
        params = payload["events"][0]["params"]
        assert params["success"] == "false"
        # engagement_time_msec is clamped to a positive integer.
        assert params["engagement_time_msec"] == 1

    def test_tool_name_truncated(self) -> None:
        payload = analytics.build_payload(
            "x" * 200, success=True, duration_ms=1,
        )
        assert len(payload["events"][0]["params"]["tool"]) == 100


class TestSendEvent:
    async def test_noop_when_disabled(self, monkeypatch, respx_mock) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("GA_MEASUREMENT_ID", raising=False)
        monkeypatch.delenv("PUBLIC_GA_MEASUREMENT_ID", raising=False)
        monkeypatch.delenv("GA_API_SECRET", raising=False)
        route = respx_mock.post(analytics.GA_ENDPOINT).mock(
            return_value=httpx.Response(204),
        )
        await analytics.send_event({"client_id": "x", "events": []})
        assert not route.called

    async def test_posts_with_credentials(self, monkeypatch, respx_mock) -> None:  # type: ignore[no-untyped-def]
        _enable(monkeypatch)
        route = respx_mock.post(analytics.GA_ENDPOINT).mock(
            return_value=httpx.Response(204),
        )
        payload = analytics.build_payload("search", success=True, duration_ms=5)
        await analytics.send_event(payload)
        assert route.called
        request = route.calls.last.request
        assert request.url.params["measurement_id"] == MEASUREMENT_ID
        assert request.url.params["api_secret"] == API_SECRET

    async def test_swallows_transport_errors(self, monkeypatch, respx_mock) -> None:  # type: ignore[no-untyped-def]
        _enable(monkeypatch)
        respx_mock.post(analytics.GA_ENDPOINT).mock(
            side_effect=httpx.ConnectError("boom"),
        )
        # Must not raise — telemetry failures are silent.
        await analytics.send_event(
            analytics.build_payload("search", success=True, duration_ms=5),
        )


class TestTrackToolCall:
    async def test_disabled_schedules_nothing(self, monkeypatch, respx_mock) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("GA_MEASUREMENT_ID", raising=False)
        monkeypatch.delenv("PUBLIC_GA_MEASUREMENT_ID", raising=False)
        monkeypatch.delenv("GA_API_SECRET", raising=False)
        route = respx_mock.post(analytics.GA_ENDPOINT).mock(
            return_value=httpx.Response(204),
        )
        analytics.track_tool_call("search", success=True, duration_ms=1)
        assert not route.called

    async def test_enabled_fires_event(self, monkeypatch, respx_mock) -> None:  # type: ignore[no-untyped-def]
        _enable(monkeypatch)
        route = respx_mock.post(analytics.GA_ENDPOINT).mock(
            return_value=httpx.Response(204),
        )
        analytics.track_tool_call("search", success=True, duration_ms=1)
        # Fire-and-forget: let the scheduled task run.
        for task in list(analytics._pending):
            await task
        assert route.called
