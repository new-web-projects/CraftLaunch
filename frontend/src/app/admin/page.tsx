"use client";

import Link from "next/link";
import { Globe, Package, CalendarClock, ToggleLeft, ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";

const SHORTCUTS = [
  { label: "Website Settings", href: "/admin/website-settings", icon: Globe },
  { label: "Package Settings", href: "/admin/package-settings", icon: Package },
  { label: "Booking Settings", href: "/admin/booking-settings", icon: CalendarClock },
  { label: "Feature Flags", href: "/admin/feature-flags", icon: ToggleLeft },
];

export default function AdminDashboardPage() {
  const { data: site, status } = useAdminSettings(configurationApi.site.get, configurationApi.site.update);
  const { data: flags } = useAdminSettings(configurationApi.featureFlags.get, configurationApi.featureFlags.update);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {status === "ready" && site ? `Welcome back — managing ${site.website_name}.` : "Welcome back."}
        </p>
      </div>

      {flags?.maintenance_mode && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          Maintenance mode is currently <strong>ON</strong> — the public site is showing a
          maintenance page to visitors.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {SHORTCUTS.map((shortcut) => {
          const Icon = shortcut.icon;
          return (
            <Link key={shortcut.href} href={shortcut.href}>
              <Card className="transition-colors hover:border-primary/50">
                <CardContent className="flex items-center gap-3 py-5">
                  <div className="rounded-md bg-primary/10 p-2 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="flex-1 text-sm font-medium text-foreground">{shortcut.label}</span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">About this dashboard</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Every module in the sidebar with a <strong>Soon</strong> badge has a working, admin-only
          protected route today — the management tools inside those specific modules are planned
          for a later part. Website, Brand, General, SEO, Storage, Payment, Email, and Feature
          Flags settings are fully live.
        </CardContent>
      </Card>
    </div>
  );
}
