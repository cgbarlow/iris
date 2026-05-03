# Standalone iris-mcp service (ADR-134 / SPEC-134-A).
# Build context is the repo root, so iris-client/ is a sibling.

FROM python:3.12-slim

WORKDIR /opt/render/project/src

# Copy iris-client first (iris-mcp depends on it via path source).
COPY iris-client/ iris-client/
COPY mcp/ mcp/

# uvicorn[standard] pulls httptools / websockets / uvloop for the
# best-supported uvicorn install.
RUN pip install --no-cache-dir \
      ./iris-client \
      ./mcp \
      "uvicorn[standard]>=0.30"

# Render sets PORT.
CMD ["sh", "-c", "uvicorn iris_mcp.http_main:create_app --factory --host 0.0.0.0 --port ${PORT:-10000}"]
