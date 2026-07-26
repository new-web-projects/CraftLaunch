# shared/

Cross-language source of truth for values that must mean the same
thing in both `frontend/` (TypeScript) and `backend/` (Python).

## Why duplicated files instead of one import

Next.js can't `import` a Python file and Django can't `import` a
TypeScript file, so each concept gets one file per language:

```
constants/roles.ts   constants/roles.py    (same values, two languages)
```

This is a convention, not a build-time guarantee — nothing currently
enforces the two files stay identical. If drift becomes a real problem
once more of these are added, the natural upgrade path is a small
codegen step (e.g. a single `roles.json` here, with a script that
generates both `roles.ts` and `roles.py` from it, run in CI to catch
drift). That's deliberately not built yet: Part 1 has exactly one
shared concept (roles / storage provider names) and neither side
consumes it yet, so the extra tooling isn't earning its keep until a
second and third shared value shows up.

## What goes here vs. what doesn't

- **Goes here:** enum-like values referenced by both sides (role
  names, status names, provider names), and API response shapes the
  frontend types against and the backend serializers should match
  (`types/common.ts`).
- **Doesn't go here:** anything that only one side needs. Frontend-only
  types live in `frontend/src/types`; Django model fields live in the
  relevant app's `models.py`.

## Contents

| File                     | Purpose                                             |
| ------------------------ | ---------------------------------------------------- |
| `constants/roles.ts`     | Role and storage-provider names, TypeScript side     |
| `constants/roles.py`     | Role and storage-provider names, Python side         |
| `types/common.ts`        | Shared API response shapes (pagination, errors)      |
