import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectPaymentSummary } from "@/types/payments";

function formatMoney(amount: string, currency: string): string {
  const symbol = currency === "INR" ? "₹" : `${currency} `;
  return `${symbol}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Every figure here is exactly what the backend sent — see
 * ProjectPaymentSummary / PaymentCalculationService. This component
 * does no arithmetic of its own, on purpose: the spec is explicit
 * that the frontend must display backend-provided values, not
 * recompute the authoritative amount.
 */
export function PaymentSummaryCard({ summary }: { summary: ProjectPaymentSummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Payment Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Total Amount</dt>
            <dd className="mt-1 text-lg font-semibold text-foreground">
              {formatMoney(summary.total_amount, summary.currency)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Paid</dt>
            <dd className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">
              {formatMoney(summary.amount_paid, summary.currency)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Due</dt>
            <dd className="mt-1 text-lg font-semibold text-foreground">
              {formatMoney(summary.amount_due, summary.currency)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Currency</dt>
            <dd className="mt-1 text-lg font-semibold text-foreground">{summary.currency}</dd>
          </div>
        </dl>
        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Advance (50%)</dt>
            <dd className="mt-1 text-foreground">{formatMoney(summary.advance_amount, summary.currency)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Final (50%)</dt>
            <dd className="mt-1 text-foreground">{formatMoney(summary.final_amount, summary.currency)}</dd>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}