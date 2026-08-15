import type { LucideIcon } from "lucide-react";

interface EmptyModulePlaceholderProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

/**
 * Part 4's spec asks for 20 admin modules, but only 9 need real
 * functionality this phase (see docs/ARCHITECTURE.md) — the rest are
 * explicitly "empty production-ready modules": a real route, real
 * layout, real permission protection (inherited from admin/layout.tsx),
 * and a real place in the nav, but no CRUD yet. This is that shape,
 * shared across all 11 rather than 11 near-identical page bodies.
 */
export function EmptyModulePlaceholder({ title, description, icon: Icon }: EmptyModulePlaceholderProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border py-16 text-center">
        <Icon className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">This module is coming soon</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          The route, layout, and admin-only access for this section are live — the management
          tools inside it are planned for a later part.
        </p>
      </div>
    </div>
  );
}
