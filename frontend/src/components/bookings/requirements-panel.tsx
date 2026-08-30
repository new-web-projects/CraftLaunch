"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/shared/states";
import type { CustomerRequirement } from "@/types/bookings";

interface RequirementsPanelProps {
  requirements: CustomerRequirement[];
  canAdd: boolean;
  onAddRequirement: (title: string) => Promise<void>;
}

const PRIORITY_STYLES: Record<string, string> = {
  HIGH: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  MEDIUM: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  LOW: "bg-secondary text-secondary-foreground",
};

export function RequirementsPanel({ requirements, canAdd, onAddRequirement }: RequirementsPanelProps) {
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (title.trim().length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await onAddRequirement(title.trim());
      setTitle("");
      setAdding(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't add that requirement.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      {requirements.length === 0 ? (
        <EmptyState title="No additional requirements yet" description="Add anything specific you need for this project." />
      ) : (
        <ul className="space-y-2">
          {requirements.map((req) => (
            <li key={req.id} className="flex items-start justify-between gap-2 rounded-md border border-border p-3">
              <div>
                <p className="text-sm font-medium text-foreground">{req.title}</p>
                {req.description && <p className="text-sm text-muted-foreground">{req.description}</p>}
              </div>
              <Badge className={PRIORITY_STYLES[req.priority] ?? PRIORITY_STYLES.MEDIUM}>{req.priority}</Badge>
            </li>
          ))}
        </ul>
      )}

      {canAdd &&
        (adding ? (
          <div className="space-y-2 rounded-md border border-dashed border-border p-3">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Add a contact form"
              autoFocus
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSubmit} disabled={submitting || title.trim().length === 0}>
                {submitting ? "Adding…" : "Add"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setAdding(false)} disabled={submitting}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" /> Add Requirement
          </Button>
        ))}
    </div>
  );
}