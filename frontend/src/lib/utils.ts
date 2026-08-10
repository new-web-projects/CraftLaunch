import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges Tailwind class names safely, resolving conflicting utility
 * classes (e.g. "p-2" vs "p-4") in favor of the last one supplied.
 * Standard shadcn/ui helper — every future shadcn component expects
 * this exact export at "@/lib/utils".
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Validates a `next` redirect target pulled from a query string.
 * Only same-origin relative paths are accepted — the moment a login
 * (or login-adjacent) page starts honoring caller-supplied redirect
 * targets, it becomes a classic open-redirect vector unless every
 * value is checked. Rejects anything that isn't a plain path
 * ("https://evil.com", "javascript:...", a bare "evil.com"),
 * protocol-relative URLs ("//evil.com", which browsers resolve
 * against the current scheme as if it were absolute), and backslash
 * variants ("/\evil.com") that some browsers normalize into
 * protocol-relative URLs before navigating. Callers pick the fallback
 * so each call site stays explicit about what happens on a miss.
 */
export function getSafeRedirect(next: string | null | undefined, fallback: string): string {
  if (!next) return fallback;
  if (!next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return fallback;
  }
  return next;
}