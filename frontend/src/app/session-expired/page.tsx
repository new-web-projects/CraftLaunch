import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function SessionExpiredPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium uppercase tracking-wide text-secondary-foreground">
        Session expired
      </span>
      <h1 className="text-2xl font-semibold text-foreground">You&apos;ve been signed out</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Your session ended — either it expired, or you logged out somewhere else. Log in again to
        continue.
      </p>
      <Button asChild>
        <Link href="/login">Log in</Link>
      </Button>
    </main>
  );
}