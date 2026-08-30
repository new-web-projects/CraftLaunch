import Link from "next/link";

import type { RecentActivityEvent } from "@/types/bookings";
import { EmptyState } from "@/components/shared/states";
import { Clock } from "lucide-react";

function timeAgo(isoDate: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
  const units: [number, string][] = [
    [31536000, "y"],
    [2592000, "mo"],
    [86400, "d"],
    [3600, "h"],
    [60, "m"],
  ];
  for (const [secondsInUnit, label] of units) {
    const count = Math.floor(seconds / secondsInUnit);
    if (count >= 1) return `${count}${label} ago`;
  }
  return "just now";
}

export function RecentActivityFeed({ events }: { events: RecentActivityEvent[] }) {
  if (events.length === 0) {
    return <EmptyState icon={Clock} title="No activity yet" description="Updates on your projects will show up here." />;
  }

  return (
    <ul className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="flex items-start gap-3 text-sm">
          <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          <div className="min-w-0 flex-1">
            <p className="text-foreground">
              {event.description}{" "}
              <Link href={`/bookings/${event.booking_id}`} className="font-medium text-primary hover:underline">
                {event.website_name}
              </Link>
            </p>
            <p className="text-xs text-muted-foreground">
              {event.actor?.username ?? "System"} · {timeAgo(event.created_at)}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}