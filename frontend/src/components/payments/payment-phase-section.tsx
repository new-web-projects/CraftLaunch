"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { paymentsApi } from "@/lib/payments-api";
import { openRazorpayCheckout } from "@/lib/razorpay-checkout";
import type { Payment, PaymentPhase, RazorpayCheckoutSuccessResponse } from "@/types/payments";
import { PaymentStatusBadge } from "./payment-status-badge";

type FlowState = "idle" | "opening" | "verifying" | "checking";

function formatMoney(amount: string, currency: string): string {
  const symbol = currency === "INR" ? "₹" : `${currency} `;
  return `${symbol}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface PaymentPhaseSectionProps {
  bookingId: string;
  phase: PaymentPhase;
  label: string;
  amount: string;
  currency: string;
  isEligible: boolean;
  websiteName: string;
  onCaptured: () => void;
}

/**
 * The actual "pay" flow for one phase. Handles every UX case the spec
 * calls out: closing checkout without paying, a network interruption
 * mid-verify, duplicate clicks, and "payment completed but the
 * verification response didn't come back" — that last one is why a
 * verify failure never says "payment failed" outright; only the
 * backend's own recorded status (fetched via Check Status) is ever
 * treated as authoritative.
 */
export function PaymentPhaseSection({
  bookingId,
  phase,
  label,
  amount,
  currency,
  isEligible,
  websiteName,
  onCaptured,
}: PaymentPhaseSectionProps) {
  const { user } = useAuth();
  const [payment, setPayment] = useState<Payment | null>(null);
  const [flowState, setFlowState] = useState<FlowState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dismissedNotice, setDismissedNotice] = useState(false);

  const getStatus = phase === "ADVANCE_PAYMENT" ? paymentsApi.getAdvanceStatus : paymentsApi.getFinalStatus;
  const createOrder = phase === "ADVANCE_PAYMENT" ? paymentsApi.createAdvanceOrder : paymentsApi.createFinalOrder;
  const verify = phase === "ADVANCE_PAYMENT" ? paymentsApi.verifyAdvancePayment : paymentsApi.verifyFinalPayment;

  useEffect(() => {
    // On mount (including a browser refresh mid-flow) — always ask
    // the backend what actually happened, rather than assuming
    // "idle/never started".
    getStatus(bookingId).then(setPayment).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookingId, phase]);

  const handleCheckStatus = () => {
    setFlowState("checking");
    getStatus(bookingId)
      .then((p) => {
        setPayment(p);
        if (p?.status === "CAPTURED") onCaptured();
      })
      .finally(() => setFlowState("idle"));
  };

  const handleCheckoutSuccess = async (result: RazorpayCheckoutSuccessResponse) => {
    setFlowState("verifying");
    try {
      const verified = await verify(bookingId, result);
      setPayment(verified);
      setFlowState("idle");
      onCaptured();
    } catch {
      // A verify call can fail two very different ways: the backend
      // genuinely rejected it (bad signature, amount mismatch — a
      // real failure), or the request itself never completed
      // (network interruption) even though Razorpay's side may have
      // gone through. Either way, don't tell the customer the
      // payment failed — only the backend's own recorded status,
      // fetched via Check Status, is authoritative.
      setFlowState("idle");
      setError(
        "We couldn't confirm your payment right away. If you completed checkout, use \"Check Status\" below rather than paying again."
      );
      getStatus(bookingId).then(setPayment).catch(() => undefined);
    }
  };

  const handlePayNow = async () => {
    setError(null);
    setDismissedNotice(false);
    setFlowState("opening");
    try {
      const order = await createOrder(bookingId);
      await openRazorpayCheckout({
        order,
        name: "CraftLaunch",
        description: `${label} — ${websiteName}`,
        customerName: user?.username,
        customerEmail: user?.email,
        onSuccess: handleCheckoutSuccess,
        onDismiss: () => {
          setFlowState("idle");
          setDismissedNotice(true);
        },
      });
    } catch (err) {
      setFlowState("idle");
      setError(err instanceof Error ? err.message : "Couldn't start the payment. Please try again.");
    }
  };

  const isCaptured = payment?.status === "CAPTURED";
  const isInFlight = flowState !== "idle";
  const showCheckStatus = payment?.status === "PENDING" || payment?.status === "AUTHORIZED" || Boolean(error);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{label}</CardTitle>
          {payment && <PaymentStatusBadge status={payment.status} label={payment.status_display} />}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-2xl font-semibold text-foreground">{formatMoney(amount, currency)}</p>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {dismissedNotice && !error && (
          <Alert>
            <AlertDescription>Checkout closed — no payment was made. You can try again anytime.</AlertDescription>
          </Alert>
        )}

        {isCaptured ? (
          <p className="text-sm text-emerald-600 dark:text-emerald-400">
            Payment received{payment?.captured_at ? ` on ${new Date(payment.captured_at).toLocaleDateString()}` : ""}.
          </p>
        ) : !isEligible ? (
          <p className="text-sm text-muted-foreground">Not available yet.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button onClick={handlePayNow} disabled={isInFlight}>
              {flowState === "opening" ? "Opening…" : flowState === "verifying" ? "Confirming payment…" : "Pay Now"}
            </Button>
            {showCheckStatus && (
              <Button variant="outline" onClick={handleCheckStatus} disabled={isInFlight}>
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                {flowState === "checking" ? "Checking…" : "Check Status"}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}