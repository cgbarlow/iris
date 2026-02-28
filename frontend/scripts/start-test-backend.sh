#!/bin/bash
# Start a clean backend for E2E tests.
# Kills any existing backend, removes stale data, then starts fresh.
set -e

cd "$(dirname "$0")/../../backend"

# Kill any existing backend server
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1

# Remove stale database to guarantee clean state
rm -rf data

# Start fresh backend with elevated rate limits for testing
export IRIS_RATE_LIMIT_LOGIN="${IRIS_RATE_LIMIT_LOGIN:-200}"
export IRIS_RATE_LIMIT_GENERAL="${IRIS_RATE_LIMIT_GENERAL:-500}"
export IRIS_RATE_LIMIT_REFRESH="${IRIS_RATE_LIMIT_REFRESH:-200}"
exec uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
