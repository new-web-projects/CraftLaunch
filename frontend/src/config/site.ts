/**
 * Site-wide configuration.
 *
 * The product spec requires site name, logo, support email, storage
 * provider and theme to be editable from the Admin Panel at runtime,
 * never hardcoded. That requires a Settings model + Admin API on the
 * backend, which is intentionally out of scope for Part 1 (no database
 * models yet).
 *
 * Until that API ships, `siteConfigFallback` is the single source of
 * truth for these values in the frontend — no other file should
 * hardcode the site name, support email, etc. When the Settings API
 * exists, `getSiteConfig()` is the one function that needs to change:
 * it should fetch from `${API_URL}/api/settings/public/` and fall
 * back to these values only if that request fails.
 */

export const siteConfigFallback = {
  name: "CraftLaunch",
  description:
    "Hire vetted developers to design, build and maintain your website.",
  supportEmail: "support@craftlaunch.example",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
} as const;

export type SiteConfig = typeof siteConfigFallback;

/**
 * Returns the active site configuration.
 * TODO(future part): fetch from the Admin-editable Settings API once
 * it exists; keep `siteConfigFallback` only as the last-resort fallback.
 */
export function getSiteConfig(): SiteConfig {
  return siteConfigFallback;
}
