#!/usr/bin/env bash
# CraftLaunch — GitHub Codespaces setup.
#
# Automates the full sequence that's already been verified working by
# hand: backend venv + dependencies, .env generation (secret key,
# Redis), migrations, Super Admin, frontend dependencies, and
# .env.local wired for the same-origin API proxy (see next.config.ts —
# this script does not touch that file; it must already contain
# skipTrailingSlashRedirect: true for anything here to actually work).
#
# Safe to re-run: every step checks whether it's already done before
# doing it. Run from anywhere in the repo:
#   bash scripts/codespaces-setup.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '\n--> %s\n' "$1"; }

echo "=================================================="
echo " CraftLaunch — Codespaces setup"
echo "=================================================="

if [ -z "${CODESPACE_NAME:-}" ]; then
  echo "Note: CODESPACE_NAME isn't set. This script targets GitHub"
  echo "Codespaces specifically — it'll still run outside one, but the"
  echo "generated FRONTEND_URL / NEXT_PUBLIC_SITE_URL will fall back to"
  echo "localhost instead of a forwarded Codespaces URL."
fi

for bin in python3 node npm; do
  command -v "$bin" >/dev/null || { echo "Missing required tool: $bin"; exit 1; }
done
echo "node:   $(node -v)"
echo "python: $(python3 --version)"

# ---------------------------------------------------------------------------
# Backend: virtual environment
# ---------------------------------------------------------------------------
log "Backend: virtual environment"
cd "$REPO_ROOT/backend"
if [ ! -d venv ]; then
  python3 -m venv venv
  echo "created backend/venv"
else
  echo "backend/venv already exists, skipping"
fi

# ---------------------------------------------------------------------------
# Backend: dependencies
# ---------------------------------------------------------------------------
log "Backend: installing dependencies"
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements/development.txt -q
echo "done"

# ---------------------------------------------------------------------------
# Backend: .env
# ---------------------------------------------------------------------------
log "Backend: .env"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "created backend/.env from .env.example"
else
  echo "backend/.env already exists, leaving its values as-is"
fi

# Secret key — only fill it in if it's still the blank placeholder from
# .env.example, so re-running this script never clobbers a real key.
if grep -q "^DJANGO_SECRET_KEY=$" .env; then
  SECRET_KEY=$(./venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${SECRET_KEY}|" .env
  echo "generated DJANGO_SECRET_KEY"
else
  echo "DJANGO_SECRET_KEY already set, leaving it"
fi

# DATABASE_URL — this script can't create a Neon project on your behalf.
# Stop with clear next steps rather than silently continuing broken.
if grep -q "^DATABASE_URL=$" .env; then
  echo ""
  echo "!! backend/.env: DATABASE_URL is empty."
  echo "!! Create a project at https://neon.tech, copy its connection string, then run:"
  echo "!!   sed -i \"s|^DATABASE_URL=.*|DATABASE_URL=<your-connection-string>|\" backend/.env"
  echo "!! ...then re-run this script."
  exit 1
fi

# Redis — installed natively rather than via Docker, since Codespaces'
# base image is plain Ubuntu and this is simpler for local dev.
if ! command -v redis-server >/dev/null; then
  log "Installing redis-server"
  sudo apt-get update -qq
  sudo apt-get install -y -qq redis-server
fi
if ! redis-cli ping >/dev/null 2>&1; then
  sudo service redis-server start
  echo "started redis-server"
else
  echo "redis-server already running"
fi
sed -i "s|^REDIS_URL=.*|REDIS_URL=redis://localhost:6379/0|" .env

# FRONTEND_URL — used to build links inside verification/reset emails,
# so it needs the real public URL a human will actually click, not the
# internal proxy target. Always recomputed (not conditional) so a
# renamed/recreated Codespace gets the right URL on re-run.
if [ -n "${CODESPACE_NAME:-}" ]; then
  FRONTEND_PUBLIC_URL="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
else
  FRONTEND_PUBLIC_URL="http://localhost:3000"
fi
sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=${FRONTEND_PUBLIC_URL}|" .env
echo "FRONTEND_URL=${FRONTEND_PUBLIC_URL}"

# ---------------------------------------------------------------------------
# Backend: migrations
# ---------------------------------------------------------------------------
log "Backend: running migrations"
./venv/bin/python manage.py migrate --noinput

# ---------------------------------------------------------------------------
# Backend: Super Admin (only if one doesn't already exist)
# ---------------------------------------------------------------------------
log "Backend: Super Admin"
if ./venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
import sys
sys.exit(0 if get_user_model().objects.filter(is_superuser=True).exists() else 1)
" 2>/dev/null; then
  echo "a Super Admin already exists, skipping"
else
  echo "no Super Admin yet — running createsuperuser (interactive):"
  ./venv/bin/python manage.py createsuperuser
fi

# ---------------------------------------------------------------------------
# Backend: system check
# ---------------------------------------------------------------------------
log "Backend: system check"
./venv/bin/python manage.py check

# ---------------------------------------------------------------------------
# Frontend: dependencies
# ---------------------------------------------------------------------------
log "Frontend: installing dependencies"
cd "$REPO_ROOT/frontend"
npm install --no-fund --no-audit

# ---------------------------------------------------------------------------
# Frontend: .env.local
# ---------------------------------------------------------------------------
log "Frontend: .env.local"
if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "created frontend/.env.local from .env.example"
else
  echo "frontend/.env.local already exists, leaving its values as-is"
fi

# Route API calls through next.config.ts's same-origin proxy instead of
# the backend's own forwarded URL — sidesteps CORS and cross-subdomain
# cookie behavior between Codespaces' two separately-forwarded ports.
# Requires next.config.ts to have skipTrailingSlashRedirect: true, or
# every proxied request will redirect-loop (see that file's comment).
sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=|" .env.local

if [ -n "${CODESPACE_NAME:-}" ]; then
  SITE_URL="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
else
  SITE_URL="http://localhost:3000"
fi
sed -i "s|^NEXT_PUBLIC_SITE_URL=.*|NEXT_PUBLIC_SITE_URL=${SITE_URL}|" .env.local
echo "NEXT_PUBLIC_API_URL=(empty — proxied through next.config.ts)"
echo "NEXT_PUBLIC_SITE_URL=${SITE_URL}"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=================================================="
echo " Setup complete."
echo "=================================================="
echo ""
echo "Start both dev servers, each in its own terminal:"
echo ""
echo "  Terminal 1:"
echo "    cd backend && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"
echo ""
echo "  Terminal 2:"
echo "    cd frontend && npm run dev -- -H 0.0.0.0"
echo ""
echo "Then open the forwarded port 3000 URL (see the Ports tab)."
echo "Port 8000 does not need to be public — only the Next.js proxy"
echo "running inside this Codespace talks to it."