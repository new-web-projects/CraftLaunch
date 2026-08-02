/**
 * Canonical role and enum names for CraftLaunch.
 *
 * This is the TypeScript half of a value that must mean the same thing
 * on both sides of the stack — see /shared/README.md for why this is
 * duplicated rather than imported directly, and keep this file and
 * shared/constants/roles.py in sync by hand until a codegen step
 * replaces that convention.
 *
 * ROLES is live as of Part 2: frontend/src/types/auth.ts's `Role` type
 * and backend/apps/accounts/models.py's `Role.TextChoices` both mirror
 * these exact values by hand (see this file's history for the sync
 * convention this predicts). STORAGE_PROVIDERS is still unconsumed —
 * that's a later part.
 */

export const ROLES = {
  ADMIN: "ADMIN",
  DEVELOPER: "DEVELOPER",
  CUSTOMER: "CUSTOMER",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export const STORAGE_PROVIDERS = {
  S3: "S3",
  CLOUDINARY: "CLOUDINARY",
} as const;

export type StorageProvider =
  (typeof STORAGE_PROVIDERS)[keyof typeof STORAGE_PROVIDERS];