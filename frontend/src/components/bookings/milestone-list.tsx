"use client";

import { useState } from "react";
import { Check } from "lucide-react";

import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { ProjectMilestone } from "@/types/bookings";

interface MilestoneListProps {
  bookingId: string;
  milestones: ProjectMilestone[];
  progressPercent: number;
  /** Only the assigned developer (or an admin) can toggle — the API
   * enforces this too (IsAssignedDeveloper), this just avoids showing
   * interactive checkboxes to people who'd get a 403. */
  canEdit: boolean;
  onToggle: (milestoneId: number, isCompleted: boolean) => Promise<void>;
}

export function MilestoneList({ milestones, progressPercent, canEdit, onToggle }: MilestoneListProps) {
  const [pendingId, setPendingId] = useState<number | null>(null);

  const handleToggle = async (milestone: ProjectMilestone) => {
    setPendingId(milestone.id);
    try {
      await onToggle(milestone.id, !milestone.is_completed);
    } finally {
      setPendingId(null);
    }
  };

  if (milestones.length === 0) {
    return <p className="text-sm text-muted-foreground">Milestones will appear once a developer accepts this project.</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1.5 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-medium text-foreground">{progressPercent}%</span>
        </div>
        <Progress value={progressPercent} />
      </div>

      <ul className="space-y-2">
        {milestones.map((milestone) => (
          <li key={milestone.id} className="flex items-center gap-3 rounded-md border border-border p-2.5">
            {canEdit ? (
              <Checkbox
                checked={milestone.is_completed}
                disabled={pendingId === milestone.id}
                onChange={() => handleToggle(milestone)}
                aria-label={`Mark ${milestone.stage_display} as ${milestone.is_completed ? "incomplete" : "complete"}`}
              />
            ) : (
              <span
                className={cn(
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                  milestone.is_completed ? "border-primary bg-primary text-primary-foreground" : "border-input"
                )}
              >
                {milestone.is_completed && <Check className="h-3 w-3" />}
              </span>
            )}
            <span
              className={cn(
                "text-sm",
                milestone.is_completed ? "text-foreground line-through decoration-muted-foreground/50" : "text-foreground"
              )}
            >
              {milestone.stage_display}
            </span>
            {milestone.completed_by && (
              <span className="ml-auto text-xs text-muted-foreground">by {milestone.completed_by.username}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}