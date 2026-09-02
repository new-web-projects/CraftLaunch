export type PaymentPhase = "ADVANCE_PAYMENT" | "FINAL_PAYMENT";

export type PaymentStatus =
  | "CREATED"
  | "ORDER_CREATED"
  | "PENDING"
  | "AUTHORIZED"
  | "CAPTURED"
  | "FAILED"
  | "REFUNDED"
  | "PARTIALLY_REFUNDED"
  | "CANCELLED"
  | "EXPIRED"
  | "VERIFICATION_FAILED";

export interface PaymentOrderResponse {
  id: string;
  payment_id: string;
  phase: PaymentPhase;
  razorpay_order_id: string;
  amount: string;
  amount_paise: number;
  currency: string;
  status: string;
  /** Public Razorpay Key ID only — read fresh from the backend on
   * every order creation, never a build-time env var. See
   * frontend/.env.example's Part 6 section for why. */
  razorpay_key_id: string;
  created_at: string;
}

export interface Payment {
  id: string;
  phase: PaymentPhase;
  phase_display: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  status_display: string;
  created_at: string;
  updated_at: string;
  captured_at: string | null;
  failure_reason: string;
}

export interface VerifyPaymentInput {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface ProjectPaymentSummary {
  booking_id: string;
  has_snapshot: boolean;
  total_amount: string;
  currency: string;
  advance_amount: string;
  final_amount: string;
  amount_paid: string;
  amount_due: string;
  advance_payment_id: string | null;
  advance_payment_status: PaymentStatus | null;
  final_payment_id: string | null;
  final_payment_status: PaymentStatus | null;
  is_advance_captured: boolean;
  is_final_captured: boolean;
}

export interface PaymentHistoryItem {
  id: string;
  booking_id: string;
  website_name: string;
  phase: PaymentPhase;
  phase_display: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  status_display: string;
  transaction_reference: string | null;
  created_at: string;
  captured_at: string | null;
}

/** The shape Razorpay's Checkout success handler hands back — see
 * lib/razorpay-checkout.ts. */
export interface RazorpayCheckoutSuccessResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface AdminPaymentOrderTransaction {
  id: string;
  razorpay_payment_id: string;
  status: string;
  method: string;
  verified_at: string | null;
  captured_at: string | null;
  created_at: string;
}

export interface AdminPaymentOrder {
  id: string;
  razorpay_order_id: string;
  amount: string;
  currency: string;
  receipt: string;
  status: string;
  created_at: string;
  transactions: AdminPaymentOrderTransaction[];
}

export interface AdminPayment {
  id: string;
  booking_id: string;
  website_name: string;
  customer: { id: number; username: string; full_name: string };
  phase: PaymentPhase;
  phase_display: string;
  amount: string;
  currency: string;
  status: PaymentStatus;
  status_display: string;
  failure_code: string;
  failure_reason: string;
  created_at: string;
  updated_at: string;
  captured_at: string | null;
  orders: AdminPaymentOrder[];
}