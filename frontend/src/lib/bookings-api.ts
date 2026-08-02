import { ApiError, type ApiErrorBody } from "@/types/auth";
import { apiClient, getAccessToken } from "@/lib/api-client";
import type { BookingDetail, BookingListItem, BookingTimelineEvent, CreateBookingInput, ProjectAttachment } from "@/types/bookings";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const bookingsApi = {
  list: (params?: { status__code?: string; ordering?: string }) => {
    const query = params ? `?${new URLSearchParams(params as Record<string, string>)}` : "";
    return apiClient.get<PaginatedResponse<BookingListItem>>(`/api/bookings/${query}`);
  },

  detail: (id: string) => apiClient.get<BookingDetail>(`/api/bookings/${id}/`),

  create: (input: CreateBookingInput, idempotencyKey: string) =>
    apiClient.post<BookingDetail>("/api/bookings/", input, {
      headers: { "Idempotency-Key": idempotencyKey },
    }),

  cancel: (id: string, reason?: string) =>
    apiClient.post<BookingDetail>(`/api/bookings/${id}/cancel/`, { reason }),

  timeline: (id: string) =>
    apiClient.get<PaginatedResponse<BookingTimelineEvent>>(`/api/bookings/${id}/timeline/`),

  deleteAttachment: (bookingId: string, attachmentId: string) =>
    apiClient.delete<void>(`/api/bookings/${bookingId}/attachments/${attachmentId}/`),

  /**
   * File upload needs a real multipart/form-data body (browser-set
   * Content-Type with boundary), which api-client.ts's shared
   * request() doesn't support — it always JSON-stringifies. Kept as a
   * standalone function rather than extending that shared client, so
   * Part 2's auth plumbing stays untouched; this still reuses the
   * same in-memory access token via getAccessToken().
   */
  async uploadAttachment(bookingId: string, file: File): Promise<ProjectAttachment> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/api/bookings/${bookingId}/attachments/`, {
      method: "POST",
      credentials: "include",
      headers: {
        ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
      },
      body: formData,
    });

    const data = await response.json().catch(() => undefined);
    if (!response.ok) {
      throw new ApiError(response.status, (data as ApiErrorBody) ?? { detail: response.statusText });
    }
    return data as ProjectAttachment;
  },
};