# CraftLaunch

A marketplace connecting customers who need a website built with
developers who build them: customers submit requirements, choose a
package, pay an advance, and track the project through delivery and
revisions; developers accept work, manage the timeline, and deliver it;
admins configure everything else — site branding, storage provider,
payment settings, and theme — from a single Admin Panel.

**This repository is at Part 1: Project Foundation.** Authentication,
payments, database models and every dashboard are intentionally not
implemented yet — see [Pending Features](#pending-features).

## Tech stack

| Layer     | Choice                                                          |
| --------- | ---------------------------------------------------------------- |
| Frontend  | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui |
| Backend   | Django 6.0, Django REST Framework                               |
| Database  | PostgreSQL (Neon)                                               |
| Storage   | AWS S3 or Cloudinary, admin-switchable (later part)             |
| Payments  | Razorpay (later part)                                           |
| Auth      | JWT + refresh tokens, role-based access (later part)            |

## Folder structure

```
craftlaunch/
├── frontend/       Next.js app (App Router, TypeScript, Tailwind, shadcn/ui)
├── backend/        Django project + REST API
├── shared/         Cross-language constants/types kept in sync by hand
├── deployment/     Dockerfiles, docker-compose, nginx
├── docs/           Architecture notes
├── scripts/        setup.sh, dev.sh
└── .github/        CI workflow
```

## Quick start (without Docker)

```bash
./scripts/setup.sh   # installs both stacks' dependencies
# edit backend/.env — set DATABASE_URL to a Neon Postgres connection string
./scripts/dev.sh      # runs both dev servers; Ctrl+C stops both
```

Frontend: http://localhost:3000 · Backend: http://localhost:8000/api/health/

## Quick start (Docker)

```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
# edit backend/.env — set DATABASE_URL and DJANGO_SECRET_KEY
docker compose -f deployment/docker-compose.yml up --build
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — settings structure,
  environment variable strategy, deployment topology, and the roadmap
  for Admin-editable settings.
- [`shared/README.md`](shared/README.md) — why constants are
  duplicated across `frontend/` and `backend/`, and when that should
  change.

## Pending features

Everything in the product spec beyond project scaffolding: JWT
authentication and role-based access, the Settings model + Admin Panel
that makes site name/logo/storage/payments/theme actually editable,
Razorpay integration, S3/Cloudinary storage switching, and the
customer/developer/admin dashboards themselves.
