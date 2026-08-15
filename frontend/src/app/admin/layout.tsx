"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { RequireRole } from "@/components/auth/require-role";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { AdminTopbar } from "@/components/admin/admin-topbar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <RequireAuth>
      <RequireRole roles={["ADMIN"]}>
        <div className="flex min-h-[calc(100vh-3.5rem)] w-full">
          <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <div className="flex min-w-0 flex-1 flex-col">
            <AdminTopbar onOpenSidebar={() => setSidebarOpen(true)} />
            <main className="flex-1 overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8">
              <div className="mx-auto w-full max-w-5xl">{children}</div>
            </main>
          </div>
        </div>
      </RequireRole>
    </RequireAuth>
  );
}
