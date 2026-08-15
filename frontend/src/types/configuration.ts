/**
 * Mirrors backend/apps/configuration/serializers.py field-for-field.
 * `AdminXConfig` names are deliberately distinct from the narrower
 * `SiteConfig` type in @/config/site.ts — that one is the public,
 * four-field shape every page can safely read; these are the full
 * admin-only shapes with every field, used only under /admin.
 */

export interface PublicConfiguration {
  site: {
    website_name: string;
    tagline: string;
    description: string;
    logo_url: string;
    favicon_url: string;
    footer_logo_url: string;
    light_logo_url: string;
    dark_logo_url: string;
    primary_color: string;
    secondary_color: string;
    accent_color: string;
    default_language: string;
    timezone: string;
    date_format: string;
    currency: string;
    contact_email: string;
    support_email: string;
    support_phone: string;
    business_address: string;
    social_links: Record<string, string>;
    copyright_text: string;
    footer_text: string;
  };
  seo: {
    site_title: string;
    meta_description: string;
    meta_keywords: string;
    canonical_url: string;
    robots_directive: string;
    og_title: string;
    og_description: string;
    twitter_site: string;
    twitter_card_type: string;
    default_share_image_url: string;
    json_ld_schema: Record<string, unknown>;
  };
  feature_flags: {
    blog_enabled: boolean;
    booking_enabled: boolean;
    reviews_enabled: boolean;
    support_enabled: boolean;
    payments_enabled: boolean;
    registration_enabled: boolean;
    developer_signup_enabled: boolean;
    customer_signup_enabled: boolean;
    maintenance_mode: boolean;
  };
}

export interface AdminSiteConfig {
  website_name: string;
  tagline: string;
  description: string;
  logo_url: string;
  favicon_url: string;
  footer_logo_url: string;
  light_logo_url: string;
  dark_logo_url: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  default_language: string;
  timezone: string;
  date_format: string;
  currency: string;
  contact_email: string;
  support_email: string;
  support_phone: string;
  business_address: string;
  social_links: Record<string, string>;
  copyright_text: string;
  footer_text: string;
  updated_at: string;
}

export interface AdminSEOConfig {
  site_title: string;
  meta_description: string;
  meta_keywords: string;
  canonical_url: string;
  robots_directive: string;
  google_verification: string;
  bing_verification: string;
  og_title: string;
  og_description: string;
  facebook_domain_verification: string;
  twitter_site: string;
  twitter_card_type: string;
  default_share_image_url: string;
  json_ld_schema: Record<string, unknown>;
  updated_at: string;
}

export interface AdminStorageConfig {
  active_provider: "LOCAL" | "S3" | "CLOUDINARY";
  s3_enabled: boolean;
  cloudinary_enabled: boolean;
  s3_access_key_id: string;
  s3_secret_access_key_is_set: boolean;
  s3_bucket_name: string;
  s3_region: string;
  cloudinary_cloud_name: string;
  cloudinary_api_key: string;
  cloudinary_api_secret_is_set: boolean;
  last_tested_at: string | null;
  last_test_success: boolean | null;
  updated_at: string;
}

export interface AdminEmailConfig {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password_is_set: boolean;
  sender_name: string;
  sender_email: string;
  reply_email: string;
  use_tls: boolean;
  use_ssl: boolean;
  last_tested_at: string | null;
  last_test_success: boolean | null;
  updated_at: string;
}

export interface AdminPaymentConfig {
  razorpay_key_id: string;
  razorpay_key_secret_is_set: boolean;
  razorpay_webhook_secret_is_set: boolean;
  default_currency: string;
  mode: "SANDBOX" | "LIVE";
  is_enabled: boolean;
  last_tested_at: string | null;
  last_test_success: boolean | null;
  updated_at: string;
}

export interface AdminFeatureFlags {
  blog_enabled: boolean;
  booking_enabled: boolean;
  reviews_enabled: boolean;
  support_enabled: boolean;
  payments_enabled: boolean;
  registration_enabled: boolean;
  developer_signup_enabled: boolean;
  customer_signup_enabled: boolean;
  maintenance_mode: boolean;
  updated_at: string;
}

export type SiteAsset = "logo" | "favicon" | "footer-logo" | "light-logo" | "dark-logo";

export interface TestConnectionResult {
  success: boolean;
  detail: string;
}
