"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Menu, Bell, Zap, ChevronDown, LogOut, UserCircle } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { ThemeToggle } from "@/components/theme-toggle";
import { findAdminNavItem } from "./admin-nav-config";

interface AdminTopbarProps {
  onOpenSidebar: () => void;
}

const QUICK_ACTIONS = [
  { label: "View public site", href: "/" },
  { label: "Browse packages", href: "/packages" },
  { label: "View bookings", href: "/bookings" },
  { label: "Website settings", href: "/admin/website-settings" },
];

export function AdminTopbar({ onOpenSidebar }: AdminTopbarProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [quickActionsOpen, setQuickActionsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const currentItem = findAdminNavItem(pathname);
  const breadcrumbLabel = currentItem?.label ?? "Dashboard";

  async function handleLogout() {
    setProfileOpen(false);
    await logout();
    router.push("/login");
  }

  function closeMenus() {
    setNotificationsOpen(false);
    setQuickActionsOpen(false);
    setProfileOpen(false);
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/75">
      <button
        type="button"
        onClick={onOpenSidebar}
        className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="min-w-0 flex-1">
        <ol className="flex items-center gap-1.5 truncate text-sm">
          <li>
            <Link href="/admin" className="text-muted-foreground hover:text-foreground">
              Admin
            </Link>
          </li>
          <li className="text-muted-foreground" aria-hidden="true">
            /
          </li>
          <li className="truncate font-medium text-foreground">{breadcrumbLabel}</li>
        </ol>
      </nav>

      <div className="flex items-center gap-1">
        {/* Quick actions */}
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              const next = !quickActionsOpen;
              closeMenus();
              setQuickActionsOpen(next);
            }}
            className="flex items-center gap-1 rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            aria-haspopup="menu"
            aria-expanded={quickActionsOpen}
            aria-label="Quick actions"
          >
            <Zap className="h-4.5 w-4.5" />
          </button>
          {quickActionsOpen && (
            <div
              role="menu"
              className="absolute right-0 z-40 mt-2 w-52 rounded-md border border-border bg-popover p-1 shadow-md"
            >
              <p className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Quick actions
              </p>
              {QUICK_ACTIONS.map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  role="menuitem"
                  onClick={closeMenus}
                  className="block rounded-sm px-2 py-1.5 text-sm text-popover-foreground hover:bg-secondary"
                >
                  {action.label}
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Notifications — a real, honest empty state; no notification
            system exists yet to generate real ones, and faking sample
            data here would be worse than showing nothing. */}
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              const next = !notificationsOpen;
              closeMenus();
              setNotificationsOpen(next);
            }}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            aria-haspopup="menu"
            aria-expanded={notificationsOpen}
            aria-label="Notifications"
          >
            <Bell className="h-4.5 w-4.5" />
          </button>
          {notificationsOpen && (
            <div
              role="menu"
              className="absolute right-0 z-40 mt-2 w-64 rounded-md border border-border bg-popover p-3 shadow-md"
            >
              <p className="text-sm font-medium text-popover-foreground">Notifications</p>
              <p className="mt-1 text-sm text-muted-foreground">You&apos;re all caught up.</p>
            </div>
          )}
        </div>

        <ThemeToggle />

        {/* Profile menu */}
        <div className="relative ml-1">
          <button
            type="button"
            onClick={() => {
              const next = !profileOpen;
              closeMenus();
              setProfileOpen(next);
            }}
            className="flex items-center gap-1.5 rounded-md py-1.5 pl-1.5 pr-2 text-sm text-foreground hover:bg-secondary"
            aria-haspopup="menu"
            aria-expanded={profileOpen}
          >
            <UserCircle className="h-5 w-5 text-muted-foreground" />
            <span className="hidden max-w-[10rem] truncate sm:inline">{user?.username}</span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          {profileOpen && (
            <div
              role="menu"
              className="absolute right-0 z-40 mt-2 w-48 rounded-md border border-border bg-popover p-1 shadow-md"
            >
              <div className="px-2 py-1.5">
                <p className="truncate text-sm font-medium text-popover-foreground">{user?.username}</p>
                <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
              </div>
              <div className="my-1 h-px bg-border" />
              <Link
                href="/profile"
                role="menuitem"
                onClick={closeMenus}
                className="block rounded-sm px-2 py-1.5 text-sm text-popover-foreground hover:bg-secondary"
              >
                My profile
              </Link>
              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm text-destructive hover:bg-secondary"
              >
                <LogOut className="h-3.5 w-3.5" />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
