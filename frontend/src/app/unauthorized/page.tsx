import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function UnauthorizedPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium uppercase tracking-wide text-secondary-foreground">
        401
      </span>
      <h1 className="text-2xl font-semibold text-foreground">Sign in required</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        You need to be logged in to view this page.
      </p>
      <Button asChild>
        <Link href="/login">Log in</Link>
      </Button>
    </main>
  );
}