"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { bookingsApi } from "@/lib/bookings-api";
import { paymentsApi } from "@/lib/payments-api";
import { ApiError } from "@/types/auth";
import type { BookingDetail } from "@/types/bookings";
import type { ProjectPaymentSummary } from "@/types/payments";
import { PaymentSummaryCard } from "@/components/payments/payment-summary-card";
import { PaymentPhaseSection } from "@/components/payments/payment-phase-section";

// Statuses where the final payment is meaningfully available — mirrors
// apps.payments.services.PaymentOrderService.FINAL_ELIGIBLE_STATUSES.
// Kept here only as a *display* hint (should the Final Payment card
// say "not available yet" or show a Pay button); the backend is what
// actually enforces this on order creation either way.
const FINAL_ELIGIBLE_STATUSES = ["ready_for_delivery", "delivered", "completed"];
const ADVANCE_ELIGIBLE_STATUSES = [
  "accepted", "in_progress", "waiting_for_customer", "revision_requested", "ready_for_delivery", "delivered", "completed",
];

function PaymentPageContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [summary, setSummary] = useState<ProjectPaymentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    Promise.all([bookingsApi.detail(params.id), paymentsApi.getSummary(params.id)])
      .then(([bookingRes, summaryRes]) => {
        setBooking(bookingRes);
        setSummary(summaryRes);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/unauthorized");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Couldn't load payment details.");
      });
  }, [params.id, router]);

  useEffect(() => {
    Promise.all([bookingsApi.detail(params.id), paymentsApi.getSummary(params.id)])
      .then(([bookingRes, summaryRes]) => {
        setBooking(bookingRes);
        setSummary(summaryRes);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/unauthorized");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Couldn't load payment details.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  const refetchSummary = useCallback(() => {
    paymentsApi.getSummary(params.id).then(setSummary).catch(() => undefined);
  }, [params.id]);

  if (error) return <main className="mx-auto max-w-3xl px-6 py-12"><ErrorState message={error} onRetry={load} /></main>;
  if (!booking || !summary) return <main className="mx-auto max-w-3xl px-6 py-12"><LoadingState label="Loading payment details…" /></main>;

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-6 py-12">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link href={`/bookings/${booking.id}`}>
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Back to project
          </Link>
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Payments</h1>
        <p className="text-muted-foreground">{booking.website_name}</p>
      </div>

      <PaymentSummaryCard summary={summary} />

      <div className="grid gap-4 sm:grid-cols-2">
        <PaymentPhaseSection
          bookingId={booking.id}
          phase="ADVANCE_PAYMENT"
          label="Advance Payment"
          amount={summary.advance_amount}
          currency={summary.currency}
          isEligible={ADVANCE_ELIGIBLE_STATUSES.includes(booking.status.code)}
          websiteName={booking.website_name}
          onCaptured={refetchSummary}
        />
        <PaymentPhaseSection
          bookingId={booking.id}
          phase="FINAL_PAYMENT"
          label="Final Payment"
          amount={summary.final_amount}
          currency={summary.currency}
          isEligible={summary.is_advance_captured && FINAL_ELIGIBLE_STATUSES.includes(booking.status.code)}
          websiteName={booking.website_name}
          onCaptured={refetchSummary}
        />
      </div>
    </main>
  );
}

export default function BookingPaymentPage() {
  return (
    <RequireAuth>
      <PaymentPageContent />
    </RequireAuth>
  );
}