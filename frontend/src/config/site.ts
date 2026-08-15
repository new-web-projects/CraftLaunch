/**
 * Site-wide configuration.
 *
 * The product spec requires site name, logo, support email, storage
 * provider and theme to be editable from the Admin Panel at runtime,
 * never hardcoded. Part 4 built the Settings model + Admin API this
 * needs (apps/configuration, backend) — `getSiteConfig()` below is
 * exactly the function Part 1 said would be the one thing that needs
 * to change once that ships.
 *
 * `siteConfigFallback` stays as the last-resort default and the value
 * used anywhere still importing it directly (site-header.tsx,
 * page.tsx, layout.tsx's static metadata) — switching those call
 * sites to actually call getSiteConfig() is separate, larger work
 * (layout.tsx's metadata is static and would need Next's
 * generateMetadata() to fetch at request time; site-header.tsx is a
 * synchronous client component today). Tracked as pending, not done
 * here — this change makes the function itself correct and ready to
 * adopt, without every current caller silently starting to make a
 * network request they don't yet handle a loading/error state for.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const siteConfigFallback = {
  name: "CraftLaunch",
  description:
    "Hire vetted developers to design, build and maintain your website.",
  supportEmail: "support@craftlaunch.example",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
} as const;

export type SiteConfig = typeof siteConfigFallback;

/**
 * Returns the active site configuration: the admin-configured values
 * from `/api/settings/public/` if that request succeeds, otherwise
 * `siteConfigFallback`. Deliberately narrowed to this same four-field
 * shape even though the backend now returns much more (logo, colors,
 * social links, ...) — every current caller only expects these four
 * fields, and widening the type is a call-site-by-call-site change
 * for whenever branding/theme actually gets wired up, not something
 * to do speculatively here.
 */
export async function getSiteConfig(): Promise<SiteConfig> {
  try {
    const response = await fetch(`${API_URL}/api/settings/public/`, {
      // Public branding data — fine to cache briefly rather than
      // refetch on every request; the settings API itself is also
      // cached server-side (see apps/configuration/services.py).
      next: { revalidate: 300 },
    });
    if (!response.ok) return siteConfigFallback;

    const data = await response.json();
    const site = data?.site;
    if (!site || typeof site.website_name !== "string") return siteConfigFallback;

    return {
      name: site.website_name || siteConfigFallback.name,
      description: site.description || siteConfigFallback.description,
      supportEmail: site.support_email || siteConfigFallback.supportEmail,
      url: siteConfigFallback.url,
    };
  } catch {
    return siteConfigFallback;
  }
}
