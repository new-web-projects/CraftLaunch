import Link from "next/link";

import { StatusBadge } from "@/components/bookings/status-badge";
import { Progress } from "@/components/ui/progress";
import type { BookingListItem } from "@/types/bookings";

export function BookingSummaryRow({ booking }: { booking: BookingListItem }) {
  return (
    <Link
      href={`/bookings/${booking.id}`}
      className="flex items-center justify-between gap-4 rounded-md border border-border p-3 transition-colors hover:border-primary/50 hover:bg-accent/40"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-foreground">{booking.website_name}</p>
        <p className="truncate text-sm text-muted-foreground">{booking.business_name}</p>
        {booking.progress_percent > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <Progress value={booking.progress_percent} className="h-1.5 max-w-[140px]" />
            <span className="text-xs text-muted-foreground">{booking.progress_percent}%</span>
          </div>
        )}
      </div>
      <StatusBadge status={booking.status} />
    </Link>
  );
}