"use client";

import { useState } from "react";
import { Menu } from "lucide-react";

import { RequireAuth } from "@/components/auth/require-auth";
import { RequireRole } from "@/components/auth/require-role";
import { useAuth } from "@/contexts/auth-context";
import { DashboardSidebar } from "@/components/dashboard/dashboard-sidebar";
import { CUSTOMER_NAV, DEVELOPER_NAV } from "@/components/dashboard/dashboard-nav-config";

function DashboardShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isDeveloper = user?.role === "DEVELOPER";
  const items = isDeveloper ? DEVELOPER_NAV : CUSTOMER_NAV;

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] w-full">
      <DashboardSidebar
        items={items}
        title={isDeveloper ? "Developer Dashboard" : "My Dashboard"}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-14 items-center border-b border-border px-4 lg:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="ml-3 font-medium text-foreground">
            {isDeveloper ? "Developer Dashboard" : "My Dashboard"}
          </span>
        </div>
        <main className="flex-1 overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <RequireRole roles={["CUSTOMER", "DEVELOPER"]}>
        <DashboardShell>{children}</DashboardShell>
      </RequireRole>
    </RequireAuth>
  );
}