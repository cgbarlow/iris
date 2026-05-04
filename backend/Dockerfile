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

# Install Python dependencies. iris-client and iris-mcp install first
# so backend's lazy `attach_mcp` import succeeds.
RUN pip install --no-cache-dir -e ./iris-client -e ./mcp \
 && cd backend && pip install --no-cache-dir -e ".[supabase]"

# Render sets PORT env var
CMD cd backend && uvicorn app.main:create_app --host 0.0.0.0 --port ${PORT:-10000} --factory
