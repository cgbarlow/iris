#!/bin/bash
# Dev environment management for Iris.
# Usage: ./scripts/dev.sh [status|start|stop|restart]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

backend_pid() {
    pgrep -f "uvicorn app.main" 2>/dev/null | head -1
}

frontend_pid() {
    pgrep -f "vite dev" 2>/dev/null | head -1
}

check_backend() {
    local pid=$(backend_pid)
    if [ -n "$pid" ]; then
        # Verify it's actually responding
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "  Backend:  ${GREEN}running${NC} (pid $pid, http://localhost:8000)"
        else
            echo -e "  Backend:  ${YELLOW}starting${NC} (pid $pid, not yet healthy)"
        fi
        return 0
    else
        echo -e "  Backend:  ${RED}stopped${NC}"
        return 1
    fi
}

check_frontend() {
    local pid=$(frontend_pid)
    if [ -n "$pid" ]; then
        echo -e "  Frontend: ${GREEN}running${NC} (pid $pid, http://localhost:5173)"
        return 0
    else
        echo -e "  Frontend: ${RED}stopped${NC}"
        return 1
    fi
}

status() {
    echo "Iris Dev Environment Status:"
    echo ""
    check_backend || true
    check_frontend || true
    echo ""
}

start_backend() {
    if [ -n "$(backend_pid)" ]; then
        echo "Backend already running"
        return 0
    fi
    echo "Starting backend..."
    cd "$BACKEND_DIR"
    nohup uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 > /tmp/iris-backend.log 2>&1 &
    # Wait up to 15s for health check
    for i in $(seq 1 15); do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "  Backend:  ${GREEN}started${NC} (http://localhost:8000)"
            return 0
        fi
        sleep 1
    done
    echo -e "  Backend:  ${RED}failed to start${NC} — check /tmp/iris-backend.log"
    return 1
}

start_frontend() {
    if [ -n "$(frontend_pid)" ]; then
        echo "Frontend already running"
        return 0
    fi
    echo "Starting frontend..."
    cd "$FRONTEND_DIR"
    nohup npx vite dev --host 0.0.0.0 --port 5173 > /tmp/iris-frontend.log 2>&1 &
    sleep 3
    if [ -n "$(frontend_pid)" ]; then
        echo -e "  Frontend: ${GREEN}started${NC} (http://localhost:5173)"
    else
        echo -e "  Frontend: ${RED}failed to start${NC} — check /tmp/iris-frontend.log"
        return 1
    fi
}

stop_backend() {
    local pid=$(backend_pid)
    if [ -n "$pid" ]; then
        echo "Stopping backend (pid $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        echo -e "  Backend:  ${RED}stopped${NC}"
    else
        echo "Backend not running"
    fi
}

stop_frontend() {
    local pid=$(frontend_pid)
    if [ -n "$pid" ]; then
        echo "Stopping frontend (pid $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        echo -e "  Frontend: ${RED}stopped${NC}"
    else
        echo "Frontend not running"
    fi
}

case "${1:-status}" in
    status)
        status
        ;;
    start)
        start_backend
        start_frontend
        echo ""
        status
        ;;
    stop)
        stop_backend
        stop_frontend
        ;;
    restart)
        stop_backend
        stop_frontend
        sleep 1
        start_backend
        start_frontend
        echo ""
        status
        ;;
    *)
        echo "Usage: $0 [status|start|stop|restart]"
        exit 1
        ;;
esac
