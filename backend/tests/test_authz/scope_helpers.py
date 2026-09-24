"""Shared helpers for the collection write-scope suites (ADR-237/238/250).

The router suites authenticate as ``admin`` (who bypasses scoping), so these
helpers set up a *scoped* ``architect`` to drive enforcement end to end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

    from app.database import DatabaseManager

ARCH_PW = "ArchitectPass123!"


async def admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"}
    )
    r = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "AdminPass123!"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def create_architect(
    client: httpx.AsyncClient, admin_headers: dict[str, str], username: str = "arch"
) -> str:
    r = await client.post(
        "/api/users",
        json={"username": username, "password": ARCH_PW, "role": "architect"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def login(client: httpx.AsyncClient, username: str) -> dict[str, str]:
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": ARCH_PW}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def add_scope(db_manager: DatabaseManager, user_id: str, *collection_ids: str) -> None:
    db = db_manager.main_db
    for cid in collection_ids:
        await db.execute(
            "INSERT INTO user_collection_scope (user_id, collection_id) VALUES (?, ?)",
            (user_id, cid),
        )
    await db.commit()


async def mk_collection(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> str:
    r = await client.post("/api/collections", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def mk_set(
    client: httpx.AsyncClient, headers: dict[str, str], name: str, collection_id: str
) -> httpx.Response:
    return await client.post(
        "/api/sets", json={"name": name, "collection_id": collection_id}, headers=headers
    )


async def mk_element(
    client: httpx.AsyncClient, headers: dict[str, str], set_id: str, name: str
) -> dict:
    r = await client.post(
        "/api/elements",
        json={"element_type": "component", "name": name, "data": {}, "set_id": set_id},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()
