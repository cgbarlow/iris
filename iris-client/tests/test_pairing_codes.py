"""iris-client pairing-code methods (ADR-160, SPEC-160-A).

Verifies the create_pairing_code / exchange_pairing_code methods and
the PairingCodeResponse / ExchangedPATResponse model contracts. Real
HTTP traffic is intercepted with respx.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient
from iris_client.exceptions import IrisHTTPError
from iris_client.models.core import (
    ExchangedPATResponse,
    PairingCodeResponse,
)


class TestCreatePairingCode:
    @pytest.mark.asyncio
    async def test_returns_typed_response(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post("http://iris.test/api/auth/pairing-codes").mock(
            return_value=httpx.Response(
                201,
                json={"code": "IRIS-ABCD-EFGH", "expires_at": "2026-05-12T15:00:00+00:00"},
            ),
        )
        resp = await pat_client.create_pairing_code()
        assert isinstance(resp, PairingCodeResponse)
        assert resp.code == "IRIS-ABCD-EFGH"
        assert resp.expires_at == "2026-05-12T15:00:00+00:00"

    @pytest.mark.asyncio
    async def test_passes_client_hint_when_provided(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post("http://iris.test/api/auth/pairing-codes").mock(
            return_value=httpx.Response(
                201, json={"code": "IRIS-XXXX-YYYY", "expires_at": "2026-05-12T15:00:00+00:00"},
            ),
        )
        await pat_client.create_pairing_code(client_hint="claude-desktop")
        body = route.calls.last.request.content.decode()
        assert "claude-desktop" in body


class TestExchangePairingCode:
    @pytest.mark.asyncio
    async def test_returns_typed_response(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(
            "http://iris.test/api/auth/pairing-codes/IRIS-ABCD-EFGH/exchange",
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "token": "iris_pat_12345678_abcdefg",
                    "prefix": "12345678",
                    "expires_at": "2026-08-10T14:32:11+00:00",
                    "mode": "pairing_code",
                },
            ),
        )
        resp = await anon_client.exchange_pairing_code("IRIS-ABCD-EFGH")
        assert isinstance(resp, ExchangedPATResponse)
        assert resp.token == "iris_pat_12345678_abcdefg"
        assert resp.prefix == "12345678"
        assert resp.mode == "pairing_code"

    @pytest.mark.asyncio
    async def test_410_maps_to_iris_http_error(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(
            "http://iris.test/api/auth/pairing-codes/IRIS-DEAD-BEEF/exchange",
        ).mock(
            return_value=httpx.Response(
                410, json={"detail": "Pairing code is unknown, expired, or already exchanged."},
            ),
        )
        with pytest.raises(IrisHTTPError) as excinfo:
            await anon_client.exchange_pairing_code("IRIS-DEAD-BEEF")
        assert excinfo.value.status_code == 410

    @pytest.mark.asyncio
    async def test_permissive_model_tolerates_extra_fields(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """A future server adding a field shouldn't break old clients."""
        respx_mock.post(
            "http://iris.test/api/auth/pairing-codes/IRIS-ABCD-EFGH/exchange",
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "token": "iris_pat_12345678_abcdefg",
                    "prefix": "12345678",
                    "expires_at": "2026-08-10T14:32:11+00:00",
                    "mode": "pairing_code",
                    "future_field": "not yet known",
                },
            ),
        )
        resp = await anon_client.exchange_pairing_code("IRIS-ABCD-EFGH")
        assert resp.token == "iris_pat_12345678_abcdefg"
