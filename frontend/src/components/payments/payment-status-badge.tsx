import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { PaymentStatus } from "@/types/payments";

const STATUS_STYLES: Record<PaymentStatus, string> = {
  CREATED: "bg-secondary text-secondary-foreground",
  ORDER_CREATED: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  AUTHORIZED: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  CAPTURED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  VERIFICATION_FAILED: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  CANCELLED: "bg-secondary text-secondary-foreground",
  EXPIRED: "bg-secondary text-secondary-foreground",
  REFUNDED: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  PARTIALLY_REFUNDED: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
};

export function PaymentStatusBadge({ status, label }: { status: PaymentStatus; label?: string }) {
  return <Badge className={cn(STATUS_STYLES[status])}>{label ?? status}</Badge>;
}