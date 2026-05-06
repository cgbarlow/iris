FROM python:3.12-slim

# Install system dependencies
#   mdbtools: .eap file import (MS Access to SQLite conversion)
#   libcairo2: SVG thumbnail generation via cairosvg
RUN apt-get update && apt-get install -y --no-install-recommends mdbtools libcairo2 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/render/project/src

# Copy backend + iris-client + iris-mcp (ADR-133: backend mounts /mcp).
COPY backend/ backend/
COPY iris-client/ iris-client/
COPY mcp/ mcp/
# v5.5.6 (issue #55 follow-up): the extensions registry (sources.json /
# manifest.json) lives at the repo root and is read by the backend at
# runtime via Path(__file__).parents[3] / "extensions". Without this
# copy, /api/extensions/{id}/check-update fails with "only supported
# for github-sourced extensions" because get_source() can't find the
# file.
COPY extensions/ extensions/

# Install Python dependencies. iris-client and iris-mcp install first
# so backend's lazy `attach_mcp` import succeeds.
RUN pip install --no-cache-dir -e ./iris-client -e ./mcp \
 && cd backend && pip install --no-cache-dir -e ".[supabase]"

# Render sets PORT env var
CMD cd backend && uvicorn app.main:create_app --host 0.0.0.0 --port ${PORT:-10000} --factory
