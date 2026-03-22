FROM python:3.11-slim

# Install system dependencies
#   mdbtools: .eap file import (MS Access to SQLite conversion)
#   libcairo2: SVG thumbnail generation via cairosvg
RUN apt-get update && apt-get install -y --no-install-recommends mdbtools libcairo2 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/render/project/src

# Copy backend code
COPY backend/ backend/

# Install Python dependencies
RUN cd backend && pip install --no-cache-dir -e ".[supabase]"

# Render sets PORT env var
CMD cd backend && uvicorn app.main:create_app --host 0.0.0.0 --port ${PORT:-10000} --factory
