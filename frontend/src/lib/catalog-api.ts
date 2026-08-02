import { apiClient } from "@/lib/api-client";
import type {
  PackageDetail,
  PackageListItem,
  ServiceCategory,
  Tag,
  Technology,
  WebsiteCategory,
  WebsiteFeature,
  WebsiteType,
} from "@/types/catalog";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const catalogApi = {
  serviceCategories: () => apiClient.get<ServiceCategory[]>("/api/catalog/service-categories/"),
  websiteCategories: () => apiClient.get<WebsiteCategory[]>("/api/catalog/website-categories/"),
  websiteTypes: () => apiClient.get<WebsiteType[]>("/api/catalog/website-types/"),
  technologies: () => apiClient.get<Technology[]>("/api/catalog/technologies/"),
  tags: () => apiClient.get<Tag[]>("/api/catalog/tags/"),
  websiteFeatures: () => apiClient.get<WebsiteFeature[]>("/api/catalog/website-features/"),

  packages: (params?: { service_category?: number; tier?: string; ordering?: string }) => {
    const query = params ? `?${new URLSearchParams(params as Record<string, string>)}` : "";
    return apiClient.get<PaginatedResponse<PackageListItem>>(`/api/catalog/packages/${query}`);
  },

  packageDetail: (slug: string) => apiClient.get<PackageDetail>(`/api/catalog/packages/${slug}/`),
};