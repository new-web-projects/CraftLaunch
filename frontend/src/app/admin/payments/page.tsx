"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";

import { PaymentStatusBadge } from "@/components/payments/payment-status-badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { paymentsApi } from "@/lib/payments-api";
import { ApiError } from "@/types/auth";
import type { AdminPayment, PaymentStatus } from "@/types/payments";
import { Receipt } from "lucide-react";

const STATUS_FILTERS: { label: string; value: PaymentStatus | "" }[] = [
  { label: "All", value: "" },
  { label: "Captured", value: "CAPTURED" },
  { label: "Failed", value: "FAILED" },
  { label: "Pending", value: "PENDING" },
  { label: "Verification Failed", value: "VERIFICATION_FAILED" },
  { label: "Refunded", value: "REFUNDED" },
];

function formatMoney(amount: string, currency: string): string {
  const symbol = currency === "INR" ? "₹" : `${currency} `;
  return `${symbol}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState<AdminPayment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<PaymentStatus | "">("");

  const load = () => {
    setError(null);
    paymentsApi
      .adminListPayments(statusFilter ? { status: statusFilter } : undefined)
      .then((res) => setPayments(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load payments."));
  };

  useEffect(() => {
    paymentsApi
      .adminListPayments(statusFilter ? { status: statusFilter } : undefined)
      .then((res) => setPayments(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load payments."));
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Payments</h1>
        <p className="text-muted-foreground">
          Read-only — financial records are never edited here. Full transaction and event detail is available in
          Django Admin.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => setStatusFilter(filter.value)}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              statusFilter === filter.value
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && !payments && <LoadingState label="Loading payments…" />}
      {!error && payments && payments.length === 0 && (
        <EmptyState icon={Receipt} title="No payments found" description="No payments match this filter." />
      )}
      {!error && payments && payments.length > 0 && (
        <div className="space-y-2">
          {payments.map((payment) => (
            <Card key={payment.id}>
              <CardContent className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-foreground">{payment.website_name}</p>
                    <Badge variant="outline" className="text-xs">
                      {payment.phase_display}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {payment.customer.full_name || payment.customer.username} ·{" "}
                    {new Date(payment.created_at).toLocaleDateString()}
                    {payment.failure_reason && ` · ${payment.failure_reason}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <p className="font-semibold text-foreground">{formatMoney(payment.amount, payment.currency)}</p>
                  <PaymentStatusBadge status={payment.status} label={payment.status_display} />
                  <Link
                    href={`/bookings/${payment.booking_id}/payment`}
                    className="text-muted-foreground hover:text-foreground"
                    title="View on booking"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}