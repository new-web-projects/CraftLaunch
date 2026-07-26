# Architecture — Part 1: Project Foundation

## Settings structure

`backend/config/settings/` is split into four modules instead of one
`settings.py`:

| Module          | Used for                                    | Database                       | `DEBUG` |
| --------------- | -------------------------------------------- | ------------------------------- | ------- |
| `base.py`       | Everything environment-agnostic (installed apps, middleware, templates, DRF defaults) | — | — |
| `development.py`| Local dev (`manage.py`'s default)            | Neon, via `DATABASE_URL`        | `True`  |
| `production.py` | Deployed environments                        | Neon, via `DATABASE_URL`        | `False` |
| `test.py`       | `manage.py test` and CI                      | In-memory SQLite                | `False` |

`base.py` never defines `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` or
`DATABASES` — each environment module supplies those explicitly. This
is deliberate: a missing environment variable should crash the
environment that needed it at startup, not silently inherit a base
default that happens to be wrong for that environment (e.g. `DEBUG`
defaulting to `True` because `production.py` forgot to override it).

`test.py` wasn't in the original task list — it's here because
"Build Verification" needs to mean something repeatable. Unit tests
run against in-memory SQLite for speed and zero setup (no Neon
credentials needed to run `manage.py test` locally), while CI
(`.github/workflows/ci.yml`) additionally runs `manage.py check --deploy`
against `production.py` with a real Postgres service container, so
engine-specific and settings-specific issues still get caught before
merge.

## Why no local Postgres container

The spec commits to Neon specifically, in every environment — not
"Postgres in prod, SQLite in dev." `docker-compose.yml` and
`docker-compose.prod.yml` both point `DATABASE_URL` at Neon rather than
running a `db:` service, and local development is expected to use a
[Neon branch](https://neon.tech/docs/introduction/branching) of the
same project rather than a locally-run database engine. This keeps dev
and prod on identical database behavior. (`test.py` is the one
exception, and only for the fast unit-test path — see above.)

## Environment variables: documented now, consumed later

Both `.env.example` files list variables in two groups: **Active in
Part 1** and **Reserved for later parts (not read by any code yet)**.
The full surface area (`STORAGE_PROVIDER`, `AWS_*`, `CLOUDINARY_*`,
`RAZORPAY_*`, JWT lifetimes) is written down now so the environment
contract is visible from day one, without wiring up the Django settings
or view logic that would actually use them — that logic belongs to the
part that implements each feature.

## The path to Admin-editable settings

The product spec requires site name, logo, support email, storage
provider, payment settings and theme to be editable from the Admin
Panel — never hardcoded. That requires a `Settings` model and an Admin
API, both explicitly out of scope for Part 1 (no database models yet).
What Part 1 does instead is shape the code so that switch-over is a
small, contained change later:

- `frontend/src/config/site.ts` exports `siteConfigFallback` and a
  `getSiteConfig()` function. Right now `getSiteConfig()` just returns
  the fallback; once the Settings API exists, only this function
  needs to change to fetch from it, with the fallback kept as a
  last-resort default if that request fails.
- `shared/constants/roles.py` documents the `Role` choices a future
  `apps/accounts` app's `User` model should use.
- Nothing in Part 1 hardcodes the site name, logo URL, or support
  email anywhere else — they all route through `siteConfigFallback`.

## Deployment topology

```
                        ┌────────────────────┐
  Browser  ───────────▶ │   nginx (80/443)   │
                        └─────────┬──────────┘
                     ┌────────────┼─────────────┐
                     ▼                          ▼
           /  (everything else)         /api/, /admin/, /static/, /media/
                     │                          │
                     ▼                          ▼
        ┌─────────────────────┐      ┌───────────────────────┐
        │ frontend (Next.js)  │      │ backend (Django+DRF)  │
        │ standalone server,  │      │ gunicorn, 3 workers    │
        │ port 3000           │      │ port 8000              │
        └─────────────────────┘      └───────────┬────────────┘
                                                   │
                                                   ▼
                                        Neon Postgres (managed,
                                        external to this compose file)
```

`deployment/docker/frontend.Dockerfile` and `backend.Dockerfile` are
the production images nginx sits in front of;
`frontend.dev.Dockerfile` / `backend.dev.Dockerfile` are lighter images
used only by `docker-compose.yml` for local hot-reload and are never
deployed.

## Known items carried forward on purpose

- **DRF permissions are wide open (`AllowAny`) globally.** There's no
  auth backend to restrict access to yet — Part 1 explicitly excludes
  authentication. Every view added before the Authentication part
  ships should be treated as public, and `REST_FRAMEWORK` in `base.py`
  is commented accordingly. This is the main thing to revisit first
  when that part starts.
- **A moderate npm audit advisory (PostCSS XSS, GHSA-qx2v-qp2m-jg93)
  ships transitively inside `next`'s own dependency tree.** `npm audit
  fix --force` "resolves" it by downgrading Next.js to a four-year-old
  release, which is not a real fix. Tracked as a dependency to watch
  for a Next.js patch release, not something to force-fix now.
- **shadcn/ui's CLI (`npx shadcn add ...`) was not run against the live
  registry during development** — the sandbox this was built in
  couldn't reach `ui.shadcn.com`. `components.json`, `src/lib/utils.ts`
  and the CSS theme tokens in `globals.css` were hand-authored to match
  what the CLI would generate, so `npx shadcn add button` (etc.) should
  work normally on a machine with normal internet access.
