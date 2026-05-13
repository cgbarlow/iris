"""PKCE (RFC 7636) S256 challenge verification.

Single helper, extracted for testability. The token endpoint receives
the original `code_verifier` from the client and must verify that
``base64url(sha256(code_verifier)) == stored_code_challenge`` in
constant time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac


def verify_s256(code_verifier: str, stored_code_challenge: str) -> bool:
    """Return True if the verifier matches the stored S256 challenge.

    Constant-time comparison guards against timing oracles. The verifier
    must be 43-128 chars per RFC 7636 §4.1; we don't enforce the upper
    bound here (cheap to hash any length; the spec range exists to
    bound brute force).
    """
    if not code_verifier or not stored_code_challenge:
        return False
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(computed, stored_code_challenge)
