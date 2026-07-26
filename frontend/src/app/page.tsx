import { ApiStatus } from "@/components/api-status";
import { siteConfigFallback } from "@/config/site";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-6 py-24 text-center">
      <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium tracking-wide text-secondary-foreground uppercase">
        Phase 1 — Foundation
      </span>

      <div className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
          {siteConfigFallback.name}
        </h1>
        <p className="mx-auto max-w-md text-balance text-muted-foreground">
          {siteConfigFallback.description}
        </p>
      </div>

      <ApiStatus />

      <p className="max-w-sm text-xs text-muted-foreground">
        The customer, developer and admin experiences ship in later parts of
        this build. This screen exists to confirm the platform foundation —
        frontend, backend and the connection between them — is working.
      </p>
    </main>
  );
}
