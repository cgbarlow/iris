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
