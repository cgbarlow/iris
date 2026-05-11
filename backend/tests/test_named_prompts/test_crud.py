"""ADR-154 / SPEC-154-A: CRUD + inheritance tests for the named-prompts API.

Each named prompt is attached to a Collection or Set. Set-scoped names
shadow Collection-scoped names with the same string in the effective
list. Anonymous read posture matches /api/collections and /api/sets;
writes require authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
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
    )


@pytest.fixture
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _make_set(client: httpx.AsyncClient, headers: dict[str, str], name: str, collection_id: str | None = None) -> dict:
    body = {"name": name}
    if collection_id is not None:
        body["collection_id"] = collection_id
    resp = await client.post("/api/sets", json=body, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


async def _make_collection(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> dict:
    resp = await client.post("/api/collections", json={"name": name}, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def _valid_prompt_body(scope_type: str, scope_id: str, name: str = "first-prompt", body: str = "Body content.") -> dict:
    return {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "name": name,
        "description": "A short description.",
        "body": body,
    }


class TestCreate:
    async def test_create_for_set_happy_path(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "DoView Book")

        resp = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"]),
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        item = resp.json()
        assert item["scope_type"] == "set"
        assert item["scope_id"] == s["id"]
        assert item["name"] == "first-prompt"
        assert item["description"] == "A short description."
        assert item["body"] == "Body content."
        assert "id" in item and item["id"]
        assert "created_at" in item and "updated_at" in item

    async def test_create_for_collection_happy_path(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        c = await _make_collection(client, headers, "NZISM")

        resp = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("collection", c["id"], name="house-rules"),
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["scope_type"] == "collection"

    async def test_create_rejects_invalid_name(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Set A")
        body = _valid_prompt_body("set", s["id"], name="Has Uppercase")

        resp = await client.post("/api/named-prompts", json=body, headers=headers)
        assert resp.status_code == 422, resp.text

    async def test_create_rejects_duplicate_name_within_scope(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Set A")

        first = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="duplicated"),
            headers=headers,
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="duplicated"),
            headers=headers,
        )
        assert second.status_code == 409, second.text

    async def test_create_404_on_unknown_scope(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", "00000000-0000-0000-0000-000000000000"),
            headers=headers,
        )
        assert resp.status_code == 404, resp.text

    async def test_create_duplicate_409_does_not_swallow_other_errors(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Regression: the duplicate-name handler must distinguish a
        UNIQUE-violation 409 from other failures (e.g. UndefinedTable on
        Supabase before m052 has been applied). UNIQUE violations get a
        clean 409 message with no driver-exception name leaked."""
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Set X")
        first = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="dup-test"),
            headers=headers,
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="dup-test"),
            headers=headers,
        )
        assert second.status_code == 409
        detail = second.json()["detail"]
        # Clean message, no driver-exception class name leaked.
        assert detail == "A named prompt with this name already exists on this scope."


class TestList:
    async def test_list_filters_by_scope(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Set A")
        await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="alpha"),
            headers=headers,
        )
        await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="bravo"),
            headers=headers,
        )

        resp = await client.get(
            "/api/named-prompts",
            params={"scope_type": "set", "scope_id": s["id"]},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert [i["name"] for i in items] == ["alpha", "bravo"]

    async def test_anonymous_can_read(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Public Set")
        await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="public-prompt"),
            headers=headers,
        )

        resp = await client.get(
            "/api/named-prompts",
            params={"scope_type": "set", "scope_id": s["id"]},
            # No auth header.
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1


class TestByScopeInheritance:
    async def test_set_inherits_parent_collection_prompts(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        c = await _make_collection(client, headers, "Parent")
        s = await _make_set(client, headers, "Child Set", collection_id=c["id"])

        await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("collection", c["id"], name="house-rules"),
            headers=headers,
        )
        await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="set-rules"),
            headers=headers,
        )

        resp = await client.get(
            "/api/named-prompts/by-scope", params={"set_id": s["id"]},
        )
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()["items"]]
        # Own first (alphabetical), then inherited (alphabetical).
        assert names == ["set-rules", "house-rules"]

    async def test_set_scoped_name_shadows_collection_scoped_name(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        c = await _make_collection(client, headers, "Parent")
        s = await _make_set(client, headers, "Child Set", collection_id=c["id"])

        # Same name on both scopes.
        await client.post(
            "/api/named-prompts",
            json={**_valid_prompt_body("collection", c["id"], name="overridden", body="C-body"),
                  "description": "from collection"},
            headers=headers,
        )
        await client.post(
            "/api/named-prompts",
            json={**_valid_prompt_body("set", s["id"], name="overridden", body="S-body"),
                  "description": "from set"},
            headers=headers,
        )

        resp = await client.get(
            "/api/named-prompts/by-scope", params={"set_id": s["id"]},
        )
        items = resp.json()["items"]
        assert len(items) == 1, items
        assert items[0]["scope_type"] == "set"
        assert items[0]["body"] == "S-body"
        assert items[0]["description"] == "from set"

    async def test_by_scope_rejects_neither_or_both(self, client: httpx.AsyncClient) -> None:
        # Neither.
        resp = await client.get("/api/named-prompts/by-scope")
        assert resp.status_code == 400

        # Both.
        resp = await client.get(
            "/api/named-prompts/by-scope",
            params={"collection_id": "x", "set_id": "y"},
        )
        assert resp.status_code == 400


class TestUpdateDelete:
    async def test_update_changes_description_and_body(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Set A")
        created = (await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="my-prompt"),
            headers=headers,
        )).json()

        resp = await client.put(
            f"/api/named-prompts/{created['id']}",
            json={"description": "Updated desc.", "body": "Updated body."},
            headers=headers,
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["description"] == "Updated desc."
        assert updated["body"] == "Updated body."
        # Scope and name are immutable — unchanged.
        assert updated["scope_id"] == s["id"]
        assert updated["name"] == "my-prompt"

    async def test_update_404_when_missing(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.put(
            "/api/named-prompts/missing-id",
            json={"description": "x", "body": "y"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_delete_returns_204_then_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = await _make_set(client, headers, "Set A")
        created = (await client.post(
            "/api/named-prompts",
            json=_valid_prompt_body("set", s["id"], name="will-delete"),
            headers=headers,
        )).json()

        first = await client.delete(f"/api/named-prompts/{created['id']}", headers=headers)
        assert first.status_code == 204

        second = await client.delete(f"/api/named-prompts/{created['id']}", headers=headers)
        assert second.status_code == 404

    async def test_get_by_id_404_for_unknown(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/named-prompts/unknown-id")
        assert resp.status_code == 404
