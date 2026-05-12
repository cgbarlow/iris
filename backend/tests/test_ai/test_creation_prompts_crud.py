"""ADR-158 (v5.13.0): POST + DELETE + extended PUT on
`/api/ai/creation-prompts` with conflict detection on the
(purpose, layer, notation, diagram_type) tuple for is_active rows.
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


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _new_prompt_body(**overrides) -> dict:
    """Default to (purpose=response_format, layer=diagram_type,
    notation=simple, diagram_type=component) — a tuple NOT covered by
    any seeded row (m051 only seeds response_format for diagram_type=
    doview_analysis), so create succeeds by default. Override
    `diagram_type` / `notation` / `purpose` to deliberately collide
    with seeded creation_format rows in conflict-detection tests.
    """
    body = {
        "name": "My New Prompt",
        "description": "Test prompt",
        "purpose": "response_format",
        "layer": "diagram_type",
        "notation": "simple",
        "diagram_type": "component",
        "prompt_text": "Some prompt body.",
        "display_order": 0,
        "is_active": True,
    }
    body.update(overrides)
    return body


class TestCreate:
    async def test_post_creates_prompt(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(name="X", notation="uml", diagram_type="class"),
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "X"
        assert body["purpose"] == "response_format"
        assert body["layer"] == "diagram_type"
        assert body["notation"] == "uml"
        assert body["diagram_type"] == "class"
        assert body["is_active"] is True
        # slug-based id
        assert body["id"] == "x"

    async def test_post_409_on_conflict_with_active_row(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The creation_format outcomes_map row is seeded and active
        with (creation_format, diagram_type, NULL, outcomes_map). A
        second active row with the same tuple should 409."""
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(
                name="Conflicting outcomes_map",
                purpose="creation_format",
                notation=None,
                diagram_type="outcomes_map",
            ),
            headers=headers,
        )
        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        assert "already exists" in detail.lower()
        assert "outcomes_map" in detail

    async def test_post_allowed_when_inactive(
        self, client: httpx.AsyncClient,
    ) -> None:
        """An inactive row can coexist with an active one on the same
        tuple — lets admins stage a replacement before swapping."""
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(
                name="Staged replacement",
                purpose="creation_format",
                notation=None,
                diagram_type="outcomes_map",
                is_active=False,
            ),
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["is_active"] is False

    async def test_post_collision_suffix_for_duplicate_names(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        first = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(name="My Prompt", notation="uml", diagram_type="class"),
            headers=headers,
        )
        second = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(name="My Prompt", notation="uml", diagram_type="sequence"),
            headers=headers,
        )
        assert first.json()["id"] == "my-prompt"
        assert second.json()["id"] == "my-prompt-2"

    async def test_post_requires_admin(self, client: httpx.AsyncClient) -> None:
        """Non-admin gets 403 (or 401 if not authenticated)."""
        resp = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(),
            # no auth header
        )
        assert resp.status_code in (401, 403)

    async def test_post_rejects_invalid_purpose(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(purpose="bogus"),
            headers=headers,
        )
        assert resp.status_code == 422


class TestDelete:
    async def test_delete_hard_deletes(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = (await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(name="To Delete", notation="archimate", diagram_type="class"),
            headers=headers,
        )).json()

        delete_resp = await client.delete(
            f"/api/ai/creation-prompts/{created['id']}", headers=headers,
        )
        assert delete_resp.status_code == 204

        # Confirm it's gone (PUT 404s on it now).
        put_resp = await client.put(
            f"/api/ai/creation-prompts/{created['id']}",
            json={"is_active": False}, headers=headers,
        )
        assert put_resp.status_code == 404

    async def test_delete_404_when_missing(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.delete(
            "/api/ai/creation-prompts/no-such-id", headers=headers,
        )
        assert resp.status_code == 404


class TestPutExtended:
    async def test_put_updates_name(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        created = (await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(name="Original", notation="c4", diagram_type="component"),
            headers=headers,
        )).json()

        resp = await client.put(
            f"/api/ai/creation-prompts/{created['id']}",
            json={"name": "Renamed", "description": "New desc"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Renamed"
        assert body["description"] == "New desc"

    async def test_put_409_on_tuple_conflict(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Changing the tuple to one already covered by another active
        creation_format row should 409."""
        headers = await _admin_headers(client)
        # Create a response_format prompt on a free tuple.
        created = (await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(
                name="My Tuple", purpose="creation_format",
                notation="archimate", diagram_type="sequence",
            ),
            headers=headers,
        )).json()
        assert created.get("id"), f"create failed: {created!r}"

        # Try moving it onto (creation_format, diagram_type, NULL, outcomes_map)
        # which is seeded and active.
        resp = await client.put(
            f"/api/ai/creation-prompts/{created['id']}",
            json={"notation": "", "diagram_type": "outcomes_map"},
            headers=headers,
        )
        assert resp.status_code == 409, resp.text

    async def test_put_allows_self_no_conflict(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Editing a row's prompt_text shouldn't self-conflict on its
        own tuple."""
        headers = await _admin_headers(client)
        # Find an existing active row.
        listing = (await client.get(
            "/api/ai/creation-prompts", headers=headers,
        )).json()
        target = next(r for r in listing if r["is_active"])

        resp = await client.put(
            f"/api/ai/creation-prompts/{target['id']}",
            json={"prompt_text": "Updated text"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["prompt_text"] == "Updated text"

    async def test_put_can_deactivate_then_create_replacement(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The staging workflow: deactivate existing, then create new."""
        headers = await _admin_headers(client)
        listing = (await client.get(
            "/api/ai/creation-prompts?purpose=creation_format",
            headers=headers,
        )).json()
        existing = next(
            r for r in listing
            if r["layer"] == "diagram_type" and r["diagram_type"] == "outcomes_map"
            and r["is_active"]
        )

        # Deactivate the existing row.
        deact = await client.put(
            f"/api/ai/creation-prompts/{existing['id']}",
            json={"is_active": False}, headers=headers,
        )
        assert deact.status_code == 200

        # Now creating a replacement on the same tuple should succeed.
        resp = await client.post(
            "/api/ai/creation-prompts",
            json=_new_prompt_body(
                name="Replacement outcomes_map",
                diagram_type="outcomes_map",
            ),
            headers=headers,
        )
        assert resp.status_code == 201
