import type { BookingTimelineEvent } from "@/types/bookings";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function Timeline({ events }: { events: BookingTimelineEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity yet.</p>;
  }

  return (
    <ol className="space-y-4">
      {events.map((event) => (
        <li key={event.id} className="flex gap-3">
          <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" aria-hidden="true" />
          <div className="flex-1 space-y-0.5">
            <p className="text-sm text-foreground">{event.description}</p>
            <p className="text-xs text-muted-foreground">
              {event.actor ? `${event.actor.full_name || event.actor.username} — ` : ""}
              {formatDate(event.created_at)}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}