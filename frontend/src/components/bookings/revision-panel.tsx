"use client";

import { useState } from "react";
import { History } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/shared/states";
import type { CreateRevisionInput, RevisionRequest } from "@/types/bookings";

const STATUS_STYLES: Record<RevisionRequest["status"], string> = {
  PENDING: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  ACKNOWLEDGED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  LIMIT_EXCEEDED: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
};

interface RevisionPanelProps {
  revisions: RevisionRequest[];
  revisionsIncluded: number;
  canRequest: boolean;
  onRequestRevision: (input: CreateRevisionInput) => Promise<void>;
}

export function RevisionPanel({ revisions, revisionsIncluded, canRequest, onRequestRevision }: RevisionPanelProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usedCount = revisions.filter((r) => r.status !== "LIMIT_EXCEEDED").length;

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      setReason("");
      setDescription("");
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (reason.trim().length < 5) {
      setError("Please describe what needs to change (at least 5 characters).");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onRequestRevision({ reason: reason.trim(), description: description.trim() });
      handleOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't submit the revision request.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {usedCount} of {revisionsIncluded} included revision{revisionsIncluded === 1 ? "" : "s"} used
        </p>
        {canRequest && (
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
            Request Revision
          </Button>
        )}
      </div>

      {revisions.length === 0 ? (
        <EmptyState icon={History} title="No revisions requested" description="Revision requests will show up here." />
      ) : (
        <ul className="space-y-2">
          {revisions.map((revision) => (
            <li key={revision.id} className="rounded-md border border-border p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-foreground">{revision.reason}</p>
                <Badge className={STATUS_STYLES[revision.status]}>{revision.status_display}</Badge>
              </div>
              {revision.description && <p className="mt-1 text-sm text-muted-foreground">{revision.description}</p>}
              <p className="mt-1 text-xs text-muted-foreground">
                {revision.requested_by?.username ?? "Customer"} · {new Date(revision.created_at).toLocaleDateString()}
              </p>
              {revision.status === "LIMIT_EXCEEDED" && (
                <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">
                  This request goes beyond what&apos;s included in your package — additional paid work is required.
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request a revision</DialogTitle>
            <DialogDescription>Tell the developer what needs to change.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="revision-reason">Reason</Label>
              <Input
                id="revision-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Change the header colour"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="revision-description">Details (optional)</Label>
              <Textarea
                id="revision-description"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Anything else the developer should know…"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Submitting…" : "Submit Request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}