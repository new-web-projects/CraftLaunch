import type { PaymentOrderResponse, RazorpayCheckoutSuccessResponse } from "@/types/payments";

/**
 * Loads Razorpay's Checkout script on demand rather than a static
 * <script> tag in the root layout — the script is only ever needed on
 * the one payment page, and the vast majority of visits to this site
 * (browsing packages, managing bookings, the whole admin panel) never
 * touch it.
 */
declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

const CHECKOUT_SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";
let loadPromise: Promise<void> | null = null;

function loadCheckoutScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = CHECKOUT_SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loadPromise = null; // allow a retry on a later call
      reject(new Error("Could not load the payment gateway. Check your connection and try again."));
    };
    document.body.appendChild(script);
  });
  return loadPromise;
}

interface OpenCheckoutOptions {
  order: PaymentOrderResponse;
  name: string;
  description: string;
  customerName?: string;
  customerEmail?: string;
  onSuccess: (result: RazorpayCheckoutSuccessResponse) => void;
  /** Called when the customer closes the checkout without paying —
   * NOT the same as a failed payment (see the payment page's "closed
   * without paying" vs "failed" state handling). */
  onDismiss: () => void;
}

/**
 * Opens Razorpay Checkout. The handler here only ever hands the raw
 * (order_id, payment_id, signature) triple up to the caller — it
 * never itself decides the payment succeeded. That decision is the
 * backend's, made by POSTing this triple to the verify endpoint; see
 * the payment page's handleCheckoutSuccess for why a Checkout
 * "success" callback firing is treated as "now go verify", not as
 * "payment confirmed".
 */
export async function openRazorpayCheckout(options: OpenCheckoutOptions): Promise<void> {
  await loadCheckoutScript();
  if (!window.Razorpay) {
    throw new Error("The payment gateway failed to load. Please refresh and try again.");
  }

  const checkout = new window.Razorpay({
    key: options.order.razorpay_key_id,
    amount: options.order.amount_paise,
    currency: options.order.currency,
    order_id: options.order.razorpay_order_id,
    name: options.name,
    description: options.description,
    prefill: {
      name: options.customerName || "",
      email: options.customerEmail || "",
    },
    handler: (response: RazorpayCheckoutSuccessResponse) => {
      options.onSuccess(response);
    },
    modal: {
      ondismiss: () => options.onDismiss(),
    },
  });

  checkout.open();
}