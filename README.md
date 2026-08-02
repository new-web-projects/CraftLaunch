# CraftLaunch

A marketplace connecting customers who need a website built with
developers who build them: customers submit requirements, choose a
package, pay an advance, and track the project through delivery and
revisions; developers accept work, manage the timeline, and deliver it;
admins configure everything else — site branding, storage provider,
payment settings, and theme — from a single Admin Panel.

**This repository is at Part 3: Core Database Architecture & Booking
Foundation.** Accounts, login, packages, and booking creation/tracking
are all live. Payments and the role dashboards are intentionally not
implemented yet — see [Pending Features](#pending-features).

## Tech stack

| Layer     | Choice                                                          |
| --------- | ---------------------------------------------------------------- |
| Frontend  | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui |
| Backend   | Django 6.0, Django REST Framework                               |
| Database  | PostgreSQL (Neon)                                               |
| Cache     | Redis (rate limiting / throttling)                               |
| Storage   | AWS S3 or Cloudinary, admin-switchable (abstraction live since Part 3) |
| Payments  | Razorpay (later part)                                           |
| Auth      | JWT + refresh tokens (httpOnly cookie), role-based access        |

## Folder structure

```
craftlaunch/
├── frontend/       Next.js app (App Router, TypeScript, Tailwind, shadcn/ui)
├── backend/        Django project + REST API
│   └── apps/
│       ├── accounts/  Users, roles, profiles, JWT auth (Part 2)
│       ├── core/      Shared abstract model mixins (Part 3)
│       ├── catalog/   Categories, types, packages, features (Part 3)
│       └── bookings/  Bookings, attachments, timeline (Part 3)
├── shared/         Cross-language constants/types kept in sync by hand
├── deployment/     Dockerfiles, docker-compose, nginx
├── docs/           Architecture notes
├── scripts/        setup.sh, dev.sh
└── .github/        CI workflow
```

## Quick start (without Docker)

```bash
./scripts/setup.sh   # installs both stacks' dependencies
# edit backend/.env — set DATABASE_URL (Neon) and REDIS_URL
./scripts/dev.sh      # runs both dev servers; Ctrl+C stops both
```

Frontend: http://localhost:3000 · Backend: http://localhost:8000/api/health/

Create the first Super Admin (only way to create further Admin
accounts — see `docs/ARCHITECTURE.md`):

```bash
cd backend && ./venv/bin/python manage.py createsuperuser
```

## Quick start (Docker)

```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
# edit backend/.env — set DATABASE_URL and DJANGO_SECRET_KEY
docker compose -f deployment/docker-compose.yml up --build
```

## Running the backend test suite

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test ./venv/bin/python manage.py test
```

99 tests: registration, login, logout/logout-all, refresh rotation,
email verification, password reset, rate limiting, role permissions
(Parts 1–2), plus package listing/creation, booking creation/
validation/cancellation, attachment upload structure, and booking
object-level permissions (Part 3).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — settings structure,
  environment variables, deployment topology, JWT/cookie design, role
  isolation, the catalog/booking data model, and the storage
  abstraction.
- [`shared/README.md`](shared/README.md) — why constants are
  duplicated across `frontend/` and `backend/`, and when that should
  change.

## Pending features

The Settings model + Admin Panel that makes site name/logo/payments/
theme actually editable, Razorpay integration, and the customer/
developer/admin dashboards themselves.