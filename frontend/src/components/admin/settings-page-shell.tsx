"use client";

import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SettingsPageShellProps {
  title: string;
  description: string;
  status: "loading" | "ready" | "error";
  saving: boolean;
  saved: boolean;
  saveError: string | null;
  onRetry: () => void;
  onSubmit: (e: React.FormEvent) => void;
  children: React.ReactNode;
  /** Extra content next to the Save button — used by Storage/Email/
   * Payment for their "Test Connection" button. */
  extraActions?: React.ReactNode;
}

export function SettingsPageShell({
  title,
  description,
  status,
  saving,
  saved,
  saveError,
  onRetry,
  onSubmit,
  children,
  extraActions,
}: SettingsPageShellProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>

      {status === "loading" && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading settings…
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center justify-between rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Couldn&apos;t load these settings.
          </span>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {status === "ready" && (
        <form onSubmit={onSubmit} className="space-y-6">
          {children}

          <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
            <Button type="submit" disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save changes
            </Button>
            {extraActions}
            {saved && !saving && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                Saved
              </span>
            )}
            {saveError && (
              <span className="flex items-center gap-1.5 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {saveError}
              </span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}

interface FieldProps {
  label: string;
  htmlFor: string;
  hint?: string;
  children: React.ReactNode;
}

/** Label + control + optional hint, the one row every settings form
 * is built from. Not a UI primitive in components/ui because it's
 * specific to this stacked label-above-input admin form layout, not
 * a general-purpose component other parts of the app would reuse. */
export function Field({ label, htmlFor, hint, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function FieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-4 sm:grid-cols-2">{children}</div>;
}

export function SectionHeading({ children }: { children: React.ReactNode }) {
  return <h2 className="text-sm font-semibold text-foreground">{children}</h2>;
}
