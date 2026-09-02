import Link from "next/link";

import { EmptyState } from "@/components/shared/states";
import { Card, CardContent } from "@/components/ui/card";
import type { PaymentHistoryItem } from "@/types/payments";
import { Receipt } from "lucide-react";
import { PaymentStatusBadge } from "./payment-status-badge";

function formatMoney(amount: string, currency: string): string {
  const symbol = currency === "INR" ? "₹" : `${currency} `;
  return `${symbol}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export function PaymentHistoryList({ payments }: { payments: PaymentHistoryItem[] }) {
  if (payments.length === 0) {
    return <EmptyState icon={Receipt} title="No payments yet" description="Your payment history will show up here." />;
  }

  return (
    <ul className="space-y-2">
      {payments.map((payment) => (
        <li key={payment.id}>
          <Link href={`/bookings/${payment.booking_id}/payment`}>
            <Card className="transition-colors hover:bg-accent">
              <CardContent className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-foreground">{payment.website_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {payment.phase_display} · {new Date(payment.created_at).toLocaleDateString()}
                    {payment.transaction_reference && ` · Ref: ${payment.transaction_reference}`}
                  </p>
                </div>
                <div className="flex items-center gap-3 sm:flex-col sm:items-end sm:gap-1">
                  <p className="font-semibold text-foreground">{formatMoney(payment.amount, payment.currency)}</p>
                  <PaymentStatusBadge status={payment.status} label={payment.status_display} />
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}