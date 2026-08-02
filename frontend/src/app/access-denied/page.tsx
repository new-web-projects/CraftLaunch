import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function AccessDeniedPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium uppercase tracking-wide text-secondary-foreground">
        403
      </span>
      <h1 className="text-2xl font-semibold text-foreground">Access denied</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Your account doesn&apos;t have permission to view this page.
      </p>
      <Button asChild>
        <Link href="/profile">Back to my profile</Link>
      </Button>
    </main>
  );
}