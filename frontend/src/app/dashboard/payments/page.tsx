"use client";

import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/shared/states";
import { PaymentHistoryList } from "@/components/payments/payment-history-list";
import { paymentsApi } from "@/lib/payments-api";
import { ApiError } from "@/types/auth";
import type { PaymentHistoryItem } from "@/types/payments";

export default function PaymentHistoryPage() {
  const [payments, setPayments] = useState<PaymentHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setPayments(null);
    paymentsApi
      .getHistory()
      .then((res) => setPayments(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load payment history."));
  };

  useEffect(() => {
    paymentsApi
      .getHistory()
      .then((res) => setPayments(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load payment history."));
  }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!payments) return <LoadingState label="Loading payment history…" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Payment History</h1>
        <p className="text-muted-foreground">Every advance and final payment across your projects.</p>
      </div>
      <PaymentHistoryList payments={payments} />
    </div>
  );
}