#!/usr/bin/env bash
# Runs both dev servers together. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

cleanup() {
  echo
  echo "==> Stopping dev servers"
  kill "$FRONTEND_PID" "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting backend on http://localhost:8000"
(cd backend && ./venv/bin/python manage.py runserver 0.0.0.0:8000) &
BACKEND_PID=$!

echo "==> Starting frontend on http://localhost:3000"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

wait "$FRONTEND_PID" "$BACKEND_PID"
