"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";

const SESSION_HINT_COOKIE = "craftlaunch_session";

function hadSessionHint(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith(`${SESSION_HINT_COOKIE}=`));
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // A hint cookie surviving past a failed refresh means there was
      // a real session that no longer validates (expired, revoked, or
      // logged out elsewhere) — worth a more specific message than
      // "you're not logged in".
      router.replace(hadSessionHint() ? "/session-expired" : "/unauthorized");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex flex-1 items-center justify-center py-24">
        <p className="text-sm text-muted-foreground">Checking your session…</p>
      </div>
    );
  }

  return <>{children}</>;
}