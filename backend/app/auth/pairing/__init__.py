"""MCP pairing-code authentication (ADR-160, SPEC-160-A).

A pairing code is a short one-shot credential generated in the web UI
and exchanged via an anonymous endpoint for a freshly minted PAT. The
flow lets MCP clients (Claude Desktop, Claude Code) authenticate
without the user editing config JSON by hand.
"""
