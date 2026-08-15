"use client";

import { useEffect } from "react";
import { configurationApi } from "@/lib/configuration-api";

/**
 * Closes the last real gap in "no hardcoded branding": Brand Settings
 * could already save primary/secondary/accent colors, but nothing
 * read them back. globals.css defines --primary/--secondary/--accent
 * as plain hex custom properties in both :root and .dark — setting
 * them via inline style on <html> here overrides both blocks at once
 * (inline styles win over stylesheet rules regardless of which class
 * is active), so one saved color works correctly in both themes
 * without needing separate light/dark variants in the data model.
 *
 * Takes effect on next full page load, not instantly on every client-
 * side navigation in an already-open tab — this runs once per mount,
 * and the App Router doesn't remount the root layout between page
 * transitions within the same session. Worth knowing, not a bug: the
 * same is true of most "restart not required" admin-configurable
 * theming — it means "no server restart", not "every open tab
 * updates without a refresh".
 *
 * *-foreground variables (text color against these backgrounds) are
 * deliberately left alone — recomputing a contrast-safe foreground
 * for an arbitrary admin-picked color is a separate, harder problem
 * this doesn't attempt; picking a very light color here can reduce
 * contrast against the existing foreground text.
 */
export function DynamicTheme() {
  useEffect(() => {
    let cancelled = false;
    configurationApi
      .public()
      .then((config) => {
        if (cancelled) return;
        const { primary_color, secondary_color, accent_color } = config.site;
        const root = document.documentElement.style;
        if (primary_color) root.setProperty("--primary", primary_color);
        if (secondary_color) root.setProperty("--secondary", secondary_color);
        if (accent_color) root.setProperty("--accent", accent_color);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
