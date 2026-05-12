"""iris_authenticate MCP tool tests (ADR-160, SPEC-160-A)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools, token_store

BASE = "http://iris.test"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    return tmp_path


class TestInvalidCredential:
    @pytest.mark.asyncio
    async def test_empty_credential_is_rejected(
        self, client: IrisClient, home: Path,
    ) -> None:
        result = await tools.dispatch("iris_authenticate", client, {"credential": ""})
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "invalid_credential"

    @pytest.mark.asyncio
    async def test_unrecognised_prefix_is_rejected(
        self, client: IrisClient, home: Path,
    ) -> None:
        result = await tools.dispatch(
            "iris_authenticate", client, {"credential": "garbage123"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "invalid_credential"


class TestPairingCodePath:
    @pytest.mark.asyncio
    async def test_happy_path_persists_and_updates_in_process_token(
        self, client: IrisClient, home: Path, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(
            f"{BASE}/api/auth/pairing-codes/IRIS-ABCD-EFGH/exchange",
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "token": "iris_pat_12345678_xyz",
                    "prefix": "12345678",
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "mode": "pairing_code",
                },
            ),
        )
        result = await tools.dispatch(
            "iris_authenticate", client, {"credential": "IRIS-ABCD-EFGH"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is True
        assert body["mode"] == "pairing_code"
        assert body["expires_at"] == "2099-01-01T00:00:00+00:00"

        # File persisted, in-process token updated.
        assert token_store.load_token(BASE) == "iris_pat_12345678_xyz"
        assert client.token == "iris_pat_12345678_xyz"

    @pytest.mark.asyncio
    async def test_case_insensitive_pairing_code(
        self, client: IrisClient, home: Path, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(
            f"{BASE}/api/auth/pairing-codes/IRIS-LOWER-CASE/exchange",
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "token": "iris_pat_12345678_xyz",
                    "prefix": "12345678",
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "mode": "pairing_code",
                },
            ),
        )
        # Passing the code in lowercase — handler upper-cases it.
        result = await tools.dispatch(
            "iris_authenticate", client, {"credential": "iris-lower-case"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_410_returns_clean_error(
        self, client: IrisClient, home: Path, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(
            f"{BASE}/api/auth/pairing-codes/IRIS-DEAD-BEEF/exchange",
        ).mock(
            return_value=httpx.Response(
                410, json={"detail": "Pairing code is unknown or expired."},
            ),
        )
        result = await tools.dispatch(
            "iris_authenticate", client, {"credential": "IRIS-DEAD-BEEF"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "pairing_code_unusable"
        # Nothing persisted, in-process token unchanged.
        assert token_store.load_token(BASE) is None


class TestPATPastePath:
    @pytest.mark.asyncio
    async def test_happy_path_validates_then_persists(
        self, client: IrisClient, home: Path, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/auth/me").mock(
            return_value=httpx.Response(
                200,
                json={"id": "u1", "username": "admin", "role": "Architect"},
            ),
        )
        result = await tools.dispatch(
            "iris_authenticate", client,
            {"credential": "iris_pat_abcd1234_validlooking"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is True
        assert body["mode"] == "pat_paste"
        assert token_store.load_token(BASE) == "iris_pat_abcd1234_validlooking"
        assert client.token == "iris_pat_abcd1234_validlooking"

    @pytest.mark.asyncio
    async def test_401_returns_clean_error(
        self, client: IrisClient, home: Path, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/auth/me").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid token"}),
        )
        result = await tools.dispatch(
            "iris_authenticate", client,
            {"credential": "iris_pat_bad1234_invalid"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "pat_invalid"
        assert token_store.load_token(BASE) is None


class TestInSessionTokenPropagation:
    """v5.17.0 (ADR-162) regression test for the v5.15.0 symptom the
    user reported: `iris_authenticate` succeeded but the next write
    tool still returned `auth_required`.

    The mechanism (`IrisClient.set_token`) updates the long-lived
    client's default Authorization header. This test verifies the
    next outgoing request actually carries the new bearer — closing
    the gap in v5.15.0's `test_happy_path_persists_and_updates_
    in_process_token`, which only asserted `client.token == ...` but
    didn't verify outgoing-header propagation.
    """

    @pytest.mark.asyncio
    async def test_pairing_then_create_set_uses_new_pat_in_same_session(
        self, home: Path, respx_mock: respx.Router,
    ) -> None:
        # Long-lived client starts anonymous (mirrors the real flow
        # where __main__.py constructs the client with no IRIS_TOKEN
        # and no persisted token).
        async with IrisClient(url=BASE, token=None) as c:
            # Mock the pairing exchange.
            respx_mock.post(
                f"{BASE}/api/auth/pairing-codes/IRIS-ABCD-EFGH/exchange",
            ).mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "token": "iris_pat_freshly_minted",
                        "prefix": "abcd1234",
                        "expires_at": "2099-01-01T00:00:00+00:00",
                        "mode": "pairing_code",
                    },
                ),
            )

            # Mock POST /api/sets — gated on the exchanged PAT.
            def maybe_unauthorized(request: httpx.Request) -> httpx.Response:
                auth = request.headers.get("authorization", "")
                if auth == "Bearer iris_pat_freshly_minted":
                    return httpx.Response(
                        201,
                        json={
                            "id": "set-1",
                            "name": "X",
                            "description": None,
                            "collection_id": None,
                            "created_at": "2026-05-12T00:00:00+00:00",
                            "updated_at": "2026-05-12T00:00:00+00:00",
                        },
                    )
                return httpx.Response(401, json={"detail": "no auth"})

            respx_mock.post(f"{BASE}/api/sets").mock(
                side_effect=maybe_unauthorized,
            )

            # Step 1: dispatch iris_authenticate
            r1 = await tools.dispatch(
                "iris_authenticate", c, {"credential": "IRIS-ABCD-EFGH"},
            )
            r1_body = json.loads(r1[0].text)
            assert r1_body["success"] is True
            assert c.token == "iris_pat_freshly_minted"

            # Step 2: dispatch create_set on the SAME long-lived client.
            # The mock backend will return 401 unless the request carries
            # the new bearer. If create_set succeeds (201), the in-process
            # token propagation works end-to-end.
            r2 = await tools.dispatch("create_set", c, {"name": "X"})
            r2_body = json.loads(r2[0].text)
            assert "auth_required" not in r2_body, (
                "create_set received auth_required even though "
                "iris_authenticate succeeded — set_token didn't "
                "propagate to outgoing requests (v5.15.0 symptom)."
            )
            assert r2_body["id"] == "set-1"
