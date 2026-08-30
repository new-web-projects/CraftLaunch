import { ApiError, type ApiErrorBody } from "@/types/auth";
import { apiClient, getAccessToken } from "@/lib/api-client";
import type {
  BookingDetail,
  BookingListItem,
  BookingNote,
  BookingTimelineEvent,
  CreateBookingInput,
  CreateRevisionInput,
  CustomerDashboardData,
  CustomerRequirement,
  DeveloperDashboardData,
  NotificationEvent,
  ProjectAttachment,
  ProjectDelivery,
  ProjectMilestone,
  RevisionRequest,
  SubmitDeliveryInput,
} from "@/types/bookings";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const bookingsApi = {
  list: (params?: { status?: string; ordering?: string }) => {
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

  // ---- Part 5: dashboards ----

  customerDashboard: () => apiClient.get<CustomerDashboardData>("/api/bookings/dashboard/customer/"),
  developerDashboard: () => apiClient.get<DeveloperDashboardData>("/api/bookings/dashboard/developer/"),

  // ---- Part 5: developer project requests ----

  requests: (params?: { ordering?: string }) => {
    const query = params ? `?${new URLSearchParams(params as Record<string, string>)}` : "";
    return apiClient.get<PaginatedResponse<BookingDetail>>(`/api/bookings/requests/${query}`);
  },
  accept: (id: string) => apiClient.post<BookingDetail>(`/api/bookings/${id}/accept/`, {}),
  reject: (id: string, reason: string) =>
    apiClient.post<BookingDetail>(`/api/bookings/${id}/reject/`, { reason }),

  // ---- Part 5: assigned-developer project management ----

  start: (id: string) => apiClient.post<BookingDetail>(`/api/bookings/${id}/start/`, {}),
  markWaitingForCustomer: (id: string, note?: string) =>
    apiClient.post<BookingDetail>(`/api/bookings/${id}/mark-waiting-for-customer/`, { note }),
  markReady: (id: string, note?: string) =>
    apiClient.post<BookingDetail>(`/api/bookings/${id}/mark-ready/`, { note }),

  // ---- Part 5: milestones ----

  milestones: (id: string) => apiClient.get<ProjectMilestone[]>(`/api/bookings/${id}/milestones/`),
  updateMilestone: (id: string, milestoneId: number, isCompleted: boolean) =>
    apiClient.patch<ProjectMilestone>(`/api/bookings/${id}/milestones/${milestoneId}/`, {
      is_completed: isCompleted,
    }),

  // ---- Part 5: delivery ----

  getDelivery: (id: string) => apiClient.get<ProjectDelivery | null>(`/api/bookings/${id}/delivery/`),
  submitDelivery: (id: string, input: SubmitDeliveryInput) =>
    apiClient.post<ProjectDelivery>(`/api/bookings/${id}/delivery/`, input),
  acceptDelivery: (id: string) => apiClient.post<BookingDetail>(`/api/bookings/${id}/delivery/accept/`, {}),

  // ---- Part 5: revisions ----

  revisions: (id: string) => apiClient.get<RevisionRequest[]>(`/api/bookings/${id}/revisions/`),
  requestRevision: (id: string, input: CreateRevisionInput) =>
    apiClient.post<RevisionRequest>(`/api/bookings/${id}/revisions/`, input),

  // ---- Part 5: notifications ----

  notifications: () => apiClient.get<PaginatedResponse<NotificationEvent>>("/api/bookings/notifications/"),
  markNotificationRead: (id: number) =>
    apiClient.post<NotificationEvent>(`/api/bookings/notifications/${id}/read/`, {}),

  // ---- Part 5: notes and requirements ----

  notes: (id: string) => apiClient.get<BookingNote[]>(`/api/bookings/${id}/notes/`),
  addNote: (id: string, content: string) =>
    apiClient.post<BookingNote>(`/api/bookings/${id}/notes/`, { content }),

  requirements: (id: string) => apiClient.get<CustomerRequirement[]>(`/api/bookings/${id}/requirements/`),
  addRequirement: (id: string, input: { title: string; description?: string; priority?: string }) =>
    apiClient.post<CustomerRequirement>(`/api/bookings/${id}/requirements/`, input),
};