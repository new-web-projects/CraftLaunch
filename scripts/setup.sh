#!/usr/bin/env bash
# One-time local setup. Safe to re-run.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Frontend: installing npm dependencies"
(cd frontend && npm install)

if [ ! -f frontend/.env.local ]; then
  cp frontend/.env.example frontend/.env.local
  echo "==> Created frontend/.env.local from frontend/.env.example"
fi

echo "==> Backend: creating virtual environment (venv/) if missing"
if [ ! -d backend/venv ]; then
  python3 -m venv backend/venv
fi

echo "==> Backend: installing Python dependencies"
backend/venv/bin/pip install --upgrade pip -q
backend/venv/bin/pip install -r backend/requirements/development.txt

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "==> Created backend/.env from backend/.env.example"
  echo "    Fill in DJANGO_SECRET_KEY and DATABASE_URL before running the backend."
fi

cat <<'EOF'

Setup complete. Next steps:
  1. Edit backend/.env — set DATABASE_URL to a Neon Postgres connection string.
  2. Run ./scripts/dev.sh to start both dev servers.
EOF
