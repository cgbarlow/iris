"""v6.0.13 (ADR-173): bare 0/1 SQL literals for BOOLEAN columns crash
on Postgres but pass on SQLite. Every OAuth-related boolean column
must be set via a parameterised Python `bool`, not a bare int literal.

The token-exchange path crashed in production with:

    asyncpg.exceptions.DatatypeMismatchError:
    column "revoked" is of type boolean but expression is of type integer

at oauth/service.py:343 -> create_refresh_token's INSERT. The existing
40 OAuth tests all passed on SQLite because SQLite stores booleans as
integers and accepts both `0`/`1` and `False`/`True` interchangeably.
The bug only surfaced on Supabase (Postgres) where the BOOLEAN type
is strict.

These tests scan the source of `app.oauth.service` for the antipattern
so it can't drift back on SQLite-only test runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import app.oauth.service as oauth_service


def _service_source() -> str:
    return Path(oauth_service.__file__).read_text(encoding="utf-8")


class TestNoBareBoolLiteralsInSQL:
    def test_no_set_revoked_equals_bare_int(self) -> None:
        """Reject `SET revoked = 0` and `SET revoked = 1`. The right
        idiom is `SET revoked = ?` with True/False passed as a param."""
        src = _service_source()
        # Direct literal matches (whitespace-insensitive).
        for needle in ("revoked = 0", "revoked = 1"):
            assert needle not in src, (
                f"bare-int literal `{needle}` in OAuth service SQL: "
                f"BOOLEAN columns must be parameterised so the Postgres "
                f"driver coerces correctly (v6.0.13 / ADR-173)."
            )

    def test_no_bare_int_trailing_in_oauth_refresh_insert(self) -> None:
        """Reject INSERTs into oauth_refresh_tokens that end with a
        bare 0/1 in the VALUES list (the position is `revoked`)."""
        src = _service_source()
        # Match `INSERT INTO oauth_refresh_tokens (...) VALUES (..., 0)`
        # or `..., 1)` regardless of how many `?` placeholders precede.
        pattern = re.compile(
            r"INSERT\s+INTO\s+oauth_refresh_tokens\s*\([^)]*\)\s*"
            r"VALUES\s*\([^)]*,\s*[01]\s*\)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(src)
        assert match is None, (
            "INSERT INTO oauth_refresh_tokens has a bare int literal in "
            f"its VALUES (...) — Postgres BOOLEAN rejects this:\n\n{match.group(0) if match else ''}"  # noqa: E501
        )

    def test_create_refresh_token_passes_bool_not_int(self) -> None:
        """The INSERT in `create_refresh_token` must include a Python
        bool in its params tuple. Static evidence: source contains
        `, False)` (or `, False,`) somewhere inside the call site."""
        src = _service_source()
        # Locate the create_refresh_token function and grep its body.
        marker = "async def create_refresh_token"
        idx = src.index(marker)
        # Function body ends at the next `async def` or end of file.
        next_def = src.find("\nasync def ", idx + len(marker))
        body = src[idx:next_def] if next_def != -1 else src[idx:]
        assert ", False" in body, (
            "create_refresh_token should pass `False` (Python bool) for "
            "the `revoked` column, not a bare integer."
        )

    def test_rotate_and_revoke_pass_true_not_int(self) -> None:
        """`rotate_refresh_token` (theft kill) and `revoke_refresh_token`
        both set revoked=True. Pin that the params tuples contain a
        Python True, not the int 1."""
        src = _service_source()
        for func in ("rotate_refresh_token", "revoke_refresh_token"):
            marker = f"async def {func}"
            assert marker in src, f"missing function {func}"
            idx = src.index(marker)
            next_def = src.find("\nasync def ", idx + len(marker))
            body = src[idx:next_def] if next_def != -1 else src[idx:]
            assert "True" in body, (
                f"{func} should pass `True` (Python bool) for the "
                f"`revoked` column, not a bare integer."
            )
