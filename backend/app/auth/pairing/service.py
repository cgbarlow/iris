"""MCP pairing-code service (ADR-160, SPEC-160-A).

- `generate_code` — mints a short typeable code from the Crockford-ish
  alphabet (excludes ambiguous I/L/O/U).
- `create_pairing_code` — inserts a row with 10-minute TTL.
- `exchange_pairing_code` — looks up the code, validates state, issues
  a fresh PAT via `tokens.service.create_token`, marks the row used.

Code uniqueness is enforced at the table primary-key level; on
collision (extremely unlikely at ~38.5 bits) we retry up to 5 times.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.tokens import service as pat_service

if TYPE_CHECKING:
    import aiosqlite
    from argon2 import PasswordHasher


# Crockford-ish base32 (no I, L, O, U). 28 chars × log2 → ~4.81 bits/char.
_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"

CODE_TTL = timedelta(minutes=10)
PAT_TTL_DAYS = 90
MAX_OUTSTANDING_PER_USER = 5
MAX_GENERATION_ATTEMPTS = 5


def generate_code() -> str:
    """Mint a fresh `IRIS-XXXX-YYYY` code."""
    first = "".join(secrets.choice(_ALPHABET) for _ in range(4))
    second = "".join(secrets.choice(_ALPHABET) for _ in range(4))
    return f"IRIS-{first}-{second}"


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


async def _purge_stale_for_user(
    db: aiosqlite.Connection,
    user_id: str,
) -> None:
    """Cap a user's outstanding (unexchanged) pairing codes.

    Best-effort cleanup; runs synchronously alongside code creation so
    we don't accumulate orphaned rows. Codes older than the TTL are
    eligible for deletion regardless of count.
    """
    one_day_ago = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
    await db.execute(
        "DELETE FROM pairing_codes WHERE expires_at < ?",
        (one_day_ago,),
    )
    cursor = await db.execute(
        "SELECT code FROM pairing_codes"
        " WHERE user_id = ? AND exchanged_at IS NULL"
        " ORDER BY created_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    # The about-to-insert code will add a row, so cap pre-insert at
    # MAX-1 to land at MAX after the INSERT.
    cap_before_insert = MAX_OUTSTANDING_PER_USER - 1
    if len(rows) > cap_before_insert:
        stale_codes = [r[0] for r in rows[cap_before_insert:]]
        placeholders = ",".join("?" for _ in stale_codes)
        await db.execute(
            f"DELETE FROM pairing_codes WHERE code IN ({placeholders})",
            stale_codes,
        )


async def create_pairing_code(
    db: aiosqlite.Connection,
    user_id: str,
    client_hint: str | None = None,
) -> dict[str, str]:
    """Mint a new pairing code for `user_id`. Returns {code, expires_at}."""
    await _purge_stale_for_user(db, user_id)

    now = datetime.now(tz=UTC)
    expires_at = (now + CODE_TTL).isoformat()
    created_at = now.isoformat()

    base_name = "MCP — " + now.strftime("%Y-%m-%d %H:%M") + " UTC"
    pat_name = f"{base_name} — {client_hint}" if client_hint else base_name

    last_err: Exception | None = None
    for _ in range(MAX_GENERATION_ATTEMPTS):
        code = generate_code()
        try:
            await db.execute(
                "INSERT INTO pairing_codes"
                " (code, user_id, created_at, expires_at, exchanged_at,"
                "  issued_pat_id, issued_pat_name)"
                " VALUES (?, ?, ?, ?, NULL, NULL, ?)",
                (code, user_id, created_at, expires_at, pat_name),
            )
            await db.commit()
            return {"code": code, "expires_at": expires_at}
        except Exception as e:  # noqa: BLE001 — sqlite IntegrityError on PK collision
            last_err = e
            continue

    raise RuntimeError(
        f"Failed to mint a unique pairing code after {MAX_GENERATION_ATTEMPTS}"
        f" attempts: {last_err!r}",
    )


async def exchange_pairing_code(
    db: aiosqlite.Connection,
    code: str,
    hasher: PasswordHasher,
) -> dict[str, Any] | None:
    """Exchange `code` for a fresh PAT.

    Returns the PAT payload (`{token, prefix, expires_at}`) on success,
    or None if the code is unknown / expired / already exchanged.
    """
    now_iso = _utcnow_iso()

    cursor = await db.execute(
        "SELECT user_id, expires_at, exchanged_at, issued_pat_name"
        " FROM pairing_codes WHERE code = ?",
        (code,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    user_id, expires_at, exchanged_at, pat_name = row

    if exchanged_at is not None:
        return None
    if expires_at <= now_iso:
        return None

    expires_at_dt = datetime.now(tz=UTC) + timedelta(days=PAT_TTL_DAYS)
    pat_record = await pat_service.create_token(
        db, user_id, pat_name, expires_at_dt, hasher,
    )

    await db.execute(
        "UPDATE pairing_codes SET exchanged_at = ?, issued_pat_id = ?"
        " WHERE code = ?",
        (now_iso, pat_record["id"], code),
    )
    await db.commit()

    return {
        "token": pat_record["token"],
        "prefix": pat_record["prefix"],
        "expires_at": pat_record["expires_at"],
    }
