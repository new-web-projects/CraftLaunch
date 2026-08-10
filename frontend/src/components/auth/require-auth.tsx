"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";

const SESSION_HINT_COOKIE = "craftlaunch_session";

function hadSessionHint(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith(`${SESSION_HINT_COOKIE}=`));
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // A hint cookie surviving past a failed refresh means there was
      // a real session that no longer validates (expired, revoked, or
      // logged out elsewhere) — worth a more specific message than
      // "you're not logged in". Either way, carry the page the user
      // was trying to reach so login can send them back afterward.
      const destination = hadSessionHint() ? "/session-expired" : "/unauthorized";
      router.replace(`${destination}?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex flex-1 items-center justify-center py-24">
        <p className="text-sm text-muted-foreground">Checking your session…</p>
      </div>
    );
  }

  return <>{children}</>;
}