"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { RequireAuth } from "@/components/auth/require-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { bookingsApi } from "@/lib/bookings-api";
import type { BookingDetail } from "@/types/bookings";

function BookingSuccessContent() {
  const params = useParams<{ id: string }>();
  const [booking, setBooking] = useState<BookingDetail | null>(null);

  useEffect(() => {
    bookingsApi.detail(params.id).then(setBooking).catch(() => setBooking(null));
  }, [params.id]);

  return (
    <main className="mx-auto max-w-lg px-6 py-16 text-center">
      <CheckCircle2 className="mx-auto h-14 w-14 text-emerald-500" aria-hidden="true" />
      <h1 className="mt-6 text-2xl font-semibold tracking-tight text-foreground">Booking submitted</h1>
      <p className="mt-2 text-muted-foreground">
        {booking
          ? `We've received your booking for "${booking.website_name}". We'll be in touch shortly.`
          : "We've received your booking. We'll be in touch shortly."}
      </p>

      <Card className="mt-8 text-left">
        <CardContent className="space-y-2 pt-6 text-sm">
          <p className="text-muted-foreground">
            Next up: upload any project files (briefs, logos, reference designs) from your booking page, and
            check back for status updates as your project moves through delivery.
          </p>
        </CardContent>
      </Card>

      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <Button asChild>
          <Link href={`/bookings/${params.id}`}>View my booking</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/packages">Browse more packages</Link>
        </Button>
      </div>
    </main>
  );
}

export default function BookingSuccessPage() {
  return (
    <RequireAuth>
      <BookingSuccessContent />
    </RequireAuth>
  );
}