"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";
import type { Role } from "@/types/auth";

/**
 * Wrap RequireAuth for pages that also need a specific role — e.g.
 * <RequireAuth><RequireRole roles={["ADMIN"]}>...</RequireRole></RequireAuth>.
 * No page uses this yet (Part 2 has no role-specific pages beyond the
 * shared profile page), but it's here so the dashboards in later parts
 * don't need to reinvent it.
 */
export function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user && !roles.includes(user.role)) {
      router.replace("/access-denied");
    }
  }, [isLoading, user, roles, router]);

  if (isLoading || !user || !roles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}