import { ApiError, type ApiErrorBody } from "@/types/auth";
import { apiClient, getAccessToken } from "@/lib/api-client";
import type {
  AdminEmailConfig,
  AdminFeatureFlags,
  AdminPaymentConfig,
  AdminSEOConfig,
  AdminSiteConfig,
  AdminStorageConfig,
  PublicConfiguration,
  SiteAsset,
  TestConnectionResult,
} from "@/types/configuration";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const configurationApi = {
  public: () => apiClient.get<PublicConfiguration>("/api/settings/public/"),

  site: {
    get: () => apiClient.get<AdminSiteConfig>("/api/settings/site/"),
    update: (data: Partial<AdminSiteConfig>) =>
      apiClient.patch<AdminSiteConfig>("/api/settings/site/", data),
  },

  seo: {
    get: () => apiClient.get<AdminSEOConfig>("/api/settings/seo/"),
    update: (data: Partial<AdminSEOConfig>) =>
      apiClient.patch<AdminSEOConfig>("/api/settings/seo/", data),
  },

  storage: {
    get: () => apiClient.get<AdminStorageConfig>("/api/settings/storage/"),
    update: (data: Partial<AdminStorageConfig>) =>
      apiClient.patch<AdminStorageConfig>("/api/settings/storage/", data),
  },

  email: {
    get: () => apiClient.get<AdminEmailConfig>("/api/settings/email/"),
    update: (data: Partial<AdminEmailConfig>) =>
      apiClient.patch<AdminEmailConfig>("/api/settings/email/", data),
  },

  payment: {
    get: () => apiClient.get<AdminPaymentConfig>("/api/settings/payment/"),
    update: (data: Partial<AdminPaymentConfig>) =>
      apiClient.patch<AdminPaymentConfig>("/api/settings/payment/", data),
  },

  featureFlags: {
    get: () => apiClient.get<AdminFeatureFlags>("/api/settings/feature-flags/"),
    update: (data: Partial<AdminFeatureFlags>) =>
      apiClient.patch<AdminFeatureFlags>("/api/settings/feature-flags/", data),
  },

  /**
   * Multipart upload, same reasoning and same shape as
   * bookings-api.ts's uploadAttachment: api-client.ts's shared
   * request() always JSON-stringifies its body, so a real file
   * upload (browser-set Content-Type with boundary) has to bypass it
   * and call fetch directly, reusing only the in-memory access token.
   */
  async uploadAsset(asset: SiteAsset, file: File): Promise<{ url: string; asset: string }> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/api/settings/site/assets/${asset}/`, {
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
    return data as { url: string; asset: string };
  },

  async testStorageConnection(): Promise<TestConnectionResult> {
    return apiClient.post<TestConnectionResult>("/api/settings/storage/test/", {});
  },
  async testEmailConnection(sendTestEmail = false): Promise<TestConnectionResult> {
    return apiClient.post<TestConnectionResult>("/api/settings/email/test/", {
      send_test_email: sendTestEmail,
    });
  },
  async testPaymentConnection(): Promise<TestConnectionResult> {
    return apiClient.post<TestConnectionResult>("/api/settings/payment/test/", {});
  },
};
