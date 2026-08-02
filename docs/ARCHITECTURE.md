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

## Known items carried forward on purpose (Part 1)

- ~~**DRF permissions are wide open (`AllowAny`) globally.**~~
  **Resolved in Part 2:** `DEFAULT_PERMISSION_CLASSES` is now
  `IsAuthenticated`; individual views opt into `AllowAny` explicitly
  (register, login, refresh, forgot/reset-password, verify-email).
- ~~**A moderate npm audit advisory (PostCSS XSS) ships transitively
  inside `next`'s own dependency tree.**~~ **Resolved in Part 2** by
  upgrading to Next.js 16.2.11 — see the Part 2 npm audit notes below
  for what that upgrade actually fixed vs. what's still open.
- **shadcn/ui's CLI (`npx shadcn add ...`) was not run against the live
  registry during development** — the sandbox this was built in
  couldn't reach `ui.shadcn.com`. `components.json`, `src/lib/utils.ts`
  and the CSS theme tokens in `globals.css` were hand-authored to match
  what the CLI would generate, so `npx shadcn add button` (etc.) should
  work normally on a machine with normal internet access. Still true
  in Part 2 — all of this part's UI primitives (Input, Label, Card,
  Alert, Separator) were hand-authored the same way.

---

# Part 2: Authentication & Authorization

## JWT + cookie design

- **Access token:** returned in the login/refresh response body, kept
  in memory only (`frontend/src/lib/api-client.ts`) — never
  localStorage/sessionStorage. Lost on a full page reload by design.
- **Refresh token:** set as an httpOnly, Secure (in prod), SameSite=Lax
  cookie, scoped to `/api/auth/`. Never appears in any JSON response.
  Rotated on every use (`ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`).
- **Session-hint cookie:** a third, non-httpOnly cookie holding just
  `"1"` — nothing sensitive. Lets `src/proxy.ts` (Next.js 16's
  replacement for `middleware.ts`) and `AuthProvider` make a fast,
  non-authoritative "is it worth trying a silent refresh" decision
  without ever touching the real token. The proxy's redirect is
  explicitly documented as a UX shortcut, not a security boundary —
  the Django API enforces the real authorization on every request
  regardless of what the proxy decides.
- **"Remember me"** is enforced twice: a longer JWT lifetime
  (`JWT_REMEMBER_ME_LIFETIME_DAYS`) and, independently, the cookies
  themselves get a real `max-age` only when remembering — otherwise
  they're browser session cookies with no `max-age` at all, so they
  disappear when the browser closes even before the (shorter) token
  expiry would have kicked in.
- **Why access tokens stay short-lived:** blacklisting a refresh token
  (logout, logout-all, revoke-session) does *not* retroactively
  invalidate an access token already issued from it — that's inherent
  to how JWTs work, not a bug. `ACCESS_TOKEN_LIFETIME` defaults to 15
  minutes specifically to bound that window.

## Role isolation

Three roles (`ADMIN` / `DEVELOPER` / `CUSTOMER`) share one `User`
table (role field) but get three *separate* profile tables
(`CustomerProfile` / `DeveloperProfile` / `AdminProfile`, from a shared
abstract `BaseProfile`) rather than one shared table with a role
column — see the models.py docstring. `apps/accounts/permissions.py`
adds `IsCustomer` / `IsDeveloper` / `IsAdminRole` / `IsSuperAdmin` for
future role-gated endpoints; `IsSuperAdmin` checks Django's own
`is_superuser`, not the `role` field, since only a true Super Admin
(bootstrapped via `createsuperuser`) can create further Admins.

## Redis is now required infrastructure

Rate limiting (login throttle, password-reset throttle) and account
lockout both depend on a cache shared across all of gunicorn's worker
processes — `LocMemCache` is per-process, which would silently make a
"5/min" limit actually allow 5×workers/min in production. Both
compose files and CI now include Redis; the same Neon reasoning above
applies here too (see `docker-compose.prod.yml`'s comment: production
should point `REDIS_URL` at a managed Redis, not a bare container).

## Bugs caught by actually running this

- A missing `apps/accounts/__init__.py` silently turned the app into a
  namespace package, which broke `manage.py test`'s dotted test-label
  discovery with a confusing `NoneType` error.
- Token rotation was blacklisting the *old* refresh token after
  mutating its own jti into the new token's jti — since `blacklist()`
  reads whatever jti is currently on the object, this would have
  blacklisted the new token's jti instead of the old one, leaving the
  original refresh token silently still valid. Fixed by blacklisting
  before mutating (see `accounts/views.py` `RefreshView`).
- `remember_me` was computed at login but never stored as a token
  claim, so it silently reset to `False` on the very first refresh.
  Fixed in `accounts/jwt.py`.
- DRF's `SimpleRateThrottle.THROTTLE_RATES` is snapshotted onto the
  throttle class at import time — `override_settings` on
  `REST_FRAMEWORK` does *not* retroactively change it for an
  already-imported throttle class, even though Django's
  `setting_changed` signal makes it look like it should. The dedicated
  throttle test (`tests/test_throttling.py`) patches the class's rate
  dict directly instead.

## npm audit: two real fixes, one accepted/tracked issue

- Adding new dependencies surfaced 3 *genuine* high-severity CVEs in
  Next.js itself (not the false-positive-downgrade pattern from Part
  1) — fixed by upgrading to the just-released 16.2.11 patch.
- That still left `sharp` (Next's optional image-optimization
  dependency) on a vulnerable version, because Next.js's own declared
  range doesn't reach the patched release yet. Fixed with a
  `package.json` "overrides" entry forcing the patched version
  directly, verified the build still succeeds with it.
- **Still open, accepted:** `eslint-config-next`'s bundled
  `eslint-plugin-react`/`eslint-plugin-import`/`eslint-plugin-jsx-a11y`
  depend on a vulnerable `minimatch`/`brace-expansion` (DoS via
  unbounded glob expansion). This is a dev-tooling-only dependency —
  it never ships to the browser or the production server — so the
  real-world exposure is low. Bumping `eslint` to 10.x satisfies the
  declared peer range but was tested and found to genuinely crash
  `eslint-plugin-react` at runtime (`getFilename is not a function`),
  so it was reverted rather than shipped broken. Tracked for whenever
  `eslint-config-next` updates its own bundled plugin versions, not
  force-fixed now — same judgment call as the postcss issue in Part 1,
  for the same reason: a real, tested incompatibility beats a cleaner
  audit report.