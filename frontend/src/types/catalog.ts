export interface ServiceCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  sort_order: number;
}

export interface WebsiteCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  sort_order: number;
}

export interface WebsiteType {
  id: number;
  name: string;
  slug: string;
  description: string;
  sort_order: number;
}

export interface Technology {
  id: number;
  name: string;
  slug: string;
  icon_url: string;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
}

export interface WebsiteFeature {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
}

export type PackageTier = "BASIC" | "STANDARD" | "PREMIUM";

export interface PackageListItem {
  id: number;
  slug: string;
  name: string;
  tier: PackageTier;
  tier_display: string;
  service_category: ServiceCategory;
  starting_price: string;
  delivery_days: number;
  revision_count: number;
  technologies: Technology[];
  tags: Tag[];
}

export interface PackageFeatureItem {
  feature: WebsiteFeature;
  is_highlighted: boolean;
  sort_order: number;
}

export interface PackageDetail extends PackageListItem {
  description: string;
  support_duration_days: number;
  package_features: PackageFeatureItem[];
  status: "DRAFT" | "PUBLISHED" | "HIDDEN" | "ARCHIVED";
  visibility: "PUBLIC" | "UNLISTED" | "PRIVATE";
}