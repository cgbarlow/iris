"""OAuth 2.1 Authorization Server for iris-mcp (ADR-164, SPEC-164-A).

v6.0.0 replaces the v5.15.0 pairing-code flow with full OAuth 2.1.
iris-backend is the Authorization Server; iris-mcp is the Protected
Resource. Access tokens are JWTs signed with the existing JWT_SECRET
(HS256) — they flow through `get_current_user` unchanged. Refresh
tokens are DB-stored with family-id rotation/theft detection.
"""
