import { apiClient } from "@/lib/api-client";
import type {
  AdminPayment,
  Payment,
  PaymentHistoryItem,
  PaymentOrderResponse,
  ProjectPaymentSummary,
  VerifyPaymentInput,
} from "@/types/payments";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const paymentsApi = {
  // Every number in every response below comes straight from the
  // backend (PaymentCalculationService) — nothing here is
  // recalculated client-side. See PaymentSummaryCard/PaymentPhaseSection.

  createAdvanceOrder: (bookingId: string) =>
    apiClient.post<PaymentOrderResponse>(`/api/payments/bookings/${bookingId}/advance/order/`, {}),
  createFinalOrder: (bookingId: string) =>
    apiClient.post<PaymentOrderResponse>(`/api/payments/bookings/${bookingId}/final/order/`, {}),

  verifyAdvancePayment: (bookingId: string, input: VerifyPaymentInput) =>
    apiClient.post<Payment>(`/api/payments/bookings/${bookingId}/advance/verify/`, input),
  verifyFinalPayment: (bookingId: string, input: VerifyPaymentInput) =>
    apiClient.post<Payment>(`/api/payments/bookings/${bookingId}/final/verify/`, input),

  getAdvanceStatus: (bookingId: string) =>
    apiClient.get<Payment | null>(`/api/payments/bookings/${bookingId}/advance/status/`),
  getFinalStatus: (bookingId: string) =>
    apiClient.get<Payment | null>(`/api/payments/bookings/${bookingId}/final/status/`),

  getSummary: (bookingId: string) =>
    apiClient.get<ProjectPaymentSummary>(`/api/payments/bookings/${bookingId}/summary/`),

  getHistory: () => apiClient.get<PaginatedResponse<PaymentHistoryItem>>("/api/payments/history/"),

  // ---- Admin ----

  adminListPayments: (params?: { status?: string; phase?: string }) => {
    const query = params ? `?${new URLSearchParams(params as Record<string, string>)}` : "";
    return apiClient.get<PaginatedResponse<AdminPayment>>(`/api/payments/admin/payments/${query}`);
  },
};