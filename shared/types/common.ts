/**
 * API response shapes that both the Django backend (via DRF
 * serializers) and the Next.js frontend need to agree on. Frontend
 * code should import these from here rather than redefining them
 * locally once real endpoints exist.
 *
 * Empty of feature-specific types in Part 1 on purpose — there are no
 * endpoints yet beyond the health check, which is small enough to type
 * directly in frontend/src/types/index.ts.
 */

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiErrorResponse {
  detail: string;
  code?: string;
}
