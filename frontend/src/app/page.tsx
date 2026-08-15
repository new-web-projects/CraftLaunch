import Link from "next/link";
import { ApiStatus } from "@/components/api-status";
import { Button } from "@/components/ui/button";
import { getSiteConfig } from "@/config/site";

export default async function Home() {
  const site = await getSiteConfig();

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-6 py-24 text-center">
      <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium tracking-wide text-secondary-foreground uppercase">
        Part 4 — Admin Panel &amp; Configuration
      </span>

      <div className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
          {site.name}
        </h1>
        <p className="mx-auto max-w-md text-balance text-muted-foreground">
          {site.description}
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
        Browse <Link href="/packages" className="underline underline-offset-2 hover:text-foreground">packages</Link>,
        manage <Link href="/bookings" className="underline underline-offset-2 hover:text-foreground">bookings</Link>, or
        head to the admin panel if you have access. This screen just confirms the foundation
        underneath all of it is still working.
      </p>
    </main>
  );
}