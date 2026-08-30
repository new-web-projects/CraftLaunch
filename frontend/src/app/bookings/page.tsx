"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { X } from "lucide-react";

import { RequireAuth } from "@/components/auth/require-auth";
import { StatusBadge } from "@/components/bookings/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { bookingsApi } from "@/lib/bookings-api";
import type { BookingListItem } from "@/types/bookings";

function formatDate(iso: string | null): string {
  if (!iso) return "Not set";
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

function MyBookingsContent() {
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get("status");

  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    bookingsApi
      .list({ ordering: "-created_at", ...(statusFilter ? { status: statusFilter } : {}) })
      .then((res) => setBookings(res.results))
      .finally(() => setIsLoading(false));
  }, [statusFilter]);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">My bookings</h1>
        {statusFilter && (
          <Link href="/bookings">
            <Badge variant="outline" className="flex items-center gap-1 py-1">
              Filtered <X className="h-3 w-3" />
            </Badge>
          </Link>
        )}
      </div>

      {isLoading ? (
        <p className="mt-6 text-muted-foreground">Loading your bookings…</p>
      ) : bookings.length === 0 ? (
        <Card className="mt-6">
          <CardContent className="py-10 text-center text-muted-foreground">
            {statusFilter ? (
              <>
                No bookings match this filter.{" "}
                <Link href="/bookings" className="text-primary underline underline-offset-4">
                  Clear it
                </Link>
                .
              </>
            ) : (
              <>
                You haven&apos;t made any bookings yet.{" "}
                <Link href="/packages" className="text-primary underline underline-offset-4">
                  Browse packages
                </Link>{" "}
                to get started.
              </>
            )}
          </CardContent>
        </Card>
      ) : (
        <ul className="mt-6 space-y-3">
          {bookings.map((booking) => (
            <li key={booking.id}>
              <Link href={`/bookings/${booking.id}`}>
                <Card className="transition-colors hover:bg-accent">
                  <CardContent className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-foreground">{booking.website_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {booking.package.name} · {booking.business_name}
                      </p>
                      {booking.progress_percent > 0 && (
                        <div className="mt-2 flex max-w-[200px] items-center gap-2">
                          <Progress value={booking.progress_percent} className="h-1.5" />
                          <span className="text-xs text-muted-foreground">{booking.progress_percent}%</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-3 sm:flex-col sm:items-end sm:gap-1">
                      <StatusBadge status={booking.status} />
                      <p className="text-xs text-muted-foreground">
                        Preferred delivery: {formatDate(booking.preferred_delivery_date)}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default function MyBookingsPage() {
  return (
    <RequireAuth>
      <MyBookingsContent />
    </RequireAuth>
  );
}