"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { siteConfigFallback } from "@/config/site";

export function SiteHeader() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="font-semibold tracking-tight text-foreground">
          {siteConfigFallback.name}
        </Link>

        <nav className="flex items-center gap-2">
          {!isLoading && isAuthenticated ? (
            <>
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {user?.username}
              </span>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/profile">My Profile</Link>
              </Button>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                Log out
              </Button>
            </>
          ) : !isLoading ? (
            <>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/login">Log in</Link>
              </Button>
              <Button variant="default" size="sm" asChild>
                <Link href="/register">Sign up</Link>
              </Button>
            </>
          ) : null}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}