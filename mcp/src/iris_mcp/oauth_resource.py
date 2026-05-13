"""OAuth 2.1 Protected Resource metadata for iris-mcp (ADR-164, v6.0.0).

Per RFC 9728, a Protected Resource exposes a metadata document at
`/.well-known/oauth-protected-resource` describing where MCP clients
should go to obtain an access token. iris-mcp's HTTP transport mounts
this endpoint; the body points at iris-backend's
`/.well-known/oauth-authorization-server` (RFC 8414).

The MCP spec mandates the 401-with-`WWW-Authenticate: Bearer
resource_metadata="..."` flow — that's the trigger that tells claude.ai
(or any compliant MCP client) to start an OAuth dance.
"""

from __future__ import annotations

import os
from typing import Any


def build_resource_metadata(
    *,
    resource: str,
    authorization_server: str,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """RFC 9728 Protected Resource metadata.

    `resource` is the canonical iris-mcp URL (the resource server's
    own base URL); `authorization_server` is the iris-backend URL
    where the AS lives.
    """
    return {
        "resource": resource,
        "authorization_servers": [authorization_server],
        "scopes_supported": scopes or ["iris"],
        "bearer_methods_supported": ["header"],
    }


def www_authenticate_header(resource_metadata_url: str) -> str:
    """Build the `WWW-Authenticate` header value to attach to 401
    responses on protected MCP endpoints.

    Per MCP spec / RFC 9728: `Bearer resource_metadata="..."`.
    """
    return (
        f'Bearer resource_metadata="{resource_metadata_url}", '
        'error="invalid_token"'
    )


def resource_metadata_url_from_env(default_host: str | None = None) -> str:
    """Compute the canonical resource_metadata URL from env.

    `IRIS_MCP_PUBLIC_URL` (operator-set) wins. Falls back to the
    iris-backend URL with `/.well-known/...` appended for dev cases.
    """
    base = os.environ.get("IRIS_MCP_PUBLIC_URL") or default_host or ""
    return base.rstrip("/") + "/.well-known/oauth-protected-resource"
