"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { getSafeRedirect } from "@/lib/utils";

function UnauthorizedContent() {
  const searchParams = useSearchParams();
  // No fallback path here on purpose: if `next` is missing or fails
  // validation, we link to plain "/login" rather than force a
  // redirect target — getSafeRedirect's normal fallback is for a
  // *post-login* destination, not for this href.
  const next = getSafeRedirect(searchParams.get("next"), "");
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";

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
        <Link href={loginHref}>Log in</Link>
      </Button>
    </main>
  );
}

export default function UnauthorizedPage() {
  return (
    <Suspense fallback={null}>
      <UnauthorizedContent />
    </Suspense>
  );
}