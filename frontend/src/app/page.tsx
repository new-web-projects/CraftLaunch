import Link from "next/link";
import { ApiStatus } from "@/components/api-status";
import { Button } from "@/components/ui/button";
import { siteConfigFallback } from "@/config/site";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-6 py-24 text-center">
      <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium tracking-wide text-secondary-foreground uppercase">
        Phase 2 — Authentication
      </span>

      <div className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
          {siteConfigFallback.name}
        </h1>
        <p className="mx-auto max-w-md text-balance text-muted-foreground">
          {siteConfigFallback.description}
        </p>
      </div>

      <div className="flex gap-3">
        <Button asChild>
          <Link href="/register">Create an account</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/login">Log in</Link>
        </Button>
      </div>

      <ApiStatus />

      <p className="max-w-sm text-xs text-muted-foreground">
        The customer, developer and admin dashboards ship in later parts of
        this build. Accounts, login and profiles are live now — this screen
        just confirms the foundation underneath them is still working.
      </p>
    </main>
  );
}