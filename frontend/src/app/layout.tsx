import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { siteConfigFallback } from "@/config/site";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/contexts/auth-context";
import { SiteHeader } from "@/components/site-header";
import { DynamicTheme } from "@/components/dynamic-theme";
import "./globals.css";

/**
 * Server-side, not the client-side fetch pattern used elsewhere
 * (site-header.tsx, dynamic-theme.tsx) — metadata has to be in the
 * initial HTML response for crawlers/link previews to see it; a
 * client-side fetch after hydration would be invisible to them.
 * Falls back to the static default on any failure (backend
 * unreachable at build/request time, etc.).
 */
export async function generateMetadata(): Promise<Metadata> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(`${apiUrl}/api/settings/public/`, {
      next: { revalidate: 300 },
    });
    if (response.ok) {
      const data = await response.json();
      const title = data?.seo?.site_title || data?.site?.website_name;
      const description = data?.seo?.meta_description || data?.site?.description;
      if (title || description) {
        return {
          title: title || siteConfigFallback.name,
          description: description || siteConfigFallback.description,
        };
      }
    }
  } catch {
    // fall through to the static default below
  }
  return {
    title: siteConfigFallback.name,
    description: siteConfigFallback.description,
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider>
          <AuthProvider>
            <DynamicTheme />
            <SiteHeader />
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}