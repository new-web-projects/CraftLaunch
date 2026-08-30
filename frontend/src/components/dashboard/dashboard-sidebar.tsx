"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import type { DashboardNavItem } from "./dashboard-nav-config";

interface DashboardSidebarProps {
  items: DashboardNavItem[];
  title: string;
  open: boolean;
  onClose: () => void;
}

export function DashboardSidebar({ items, title, open, onClose }: DashboardSidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 shrink-0 overflow-y-auto border-r border-border bg-card px-4 py-6 transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label={title}
      >
        <div className="mb-6 flex items-center justify-between px-2">
          <Link href="/dashboard" className="text-lg font-semibold tracking-tight text-foreground">
            {title}
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav>
          <ul className="space-y-0.5">
            {items.map((item) => {
              // The "My Projects" links carry a query string, so exact
              // pathname equality alone would never mark them active —
              // compare the full href including search params instead.
              const isActive =
                item.href.includes("?")
                  ? `${pathname}${typeof window !== "undefined" ? window.location.search : ""}` === item.href
                  : pathname === item.href;
              const Icon = item.icon;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                      isActive
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-foreground/80 hover:bg-secondary hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>
    </>
  );
}