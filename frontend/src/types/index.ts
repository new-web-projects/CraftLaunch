/**
 * Frontend-only shared types. Types that must stay in sync with the
 * Django backend (role names, storage provider names, etc.) live in
 * /shared instead — see /shared/README.md.
 */

export interface ApiError {
  detail: string;
  code?: string;
}

export interface HealthCheckResponse {
  status: "ok";
  service: string;
  version: string;
}
