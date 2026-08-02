import type { PackageListItem, WebsiteCategory, WebsiteFeature, WebsiteType } from "./catalog";

export interface ProjectStatus {
  code: string;
  label: string;
  sort_order: number;
  is_terminal: boolean;
  color: string;
}

export interface BookingActor {
  id: number;
  username: string;
  full_name: string;
  role: "ADMIN" | "DEVELOPER" | "CUSTOMER";
}

export interface BookingRequirementItem {
  feature: WebsiteFeature;
  notes: string;
}

export interface CustomerRequirement {
  id: number;
  title: string;
  description: string;
  priority: "LOW" | "MEDIUM" | "HIGH";
  created_at: string;
}

export interface ProjectAttachment {
  id: string;
  original_filename: string;
  content_type: string;
  file_category: "IMAGE" | "PDF" | "ZIP" | "DOCX" | "SPREADSHEET" | "TEXT";
  file_size: number;
  uploaded_by: BookingActor;
  created_at: string;
}

export interface BookingTimelineEvent {
  id: number;
  event_type: string;
  event_type_display: string;
  actor: BookingActor | null;
  from_status: ProjectStatus | null;
  to_status: ProjectStatus | null;
  description: string;
  created_at: string;
}

export interface BookingNote {
  id: number;
  author: BookingActor | null;
  content: string;
  is_internal: boolean;
  created_at: string;
}

export interface DeveloperAssignment {
  id: number;
  developer: BookingActor;
  role_note: string;
  assigned_at: string;
  is_active: boolean;
}

export type BusinessType =
  | "INDIVIDUAL"
  | "STARTUP"
  | "SMALL_BUSINESS"
  | "ENTERPRISE"
  | "NON_PROFIT"
  | "OTHER";

export interface ReferenceLink {
  label?: string;
  url: string;
}

export interface BookingListItem {
  id: string;
  website_name: string;
  business_name: string;
  package: PackageListItem;
  website_category: WebsiteCategory;
  status: ProjectStatus;
  preferred_delivery_date: string | null;
  created_at: string;
}

export interface BookingDetail extends BookingListItem {
  website_type: WebsiteType | null;
  business_type: BusinessType;
  description: string;
  reference_links: ReferenceLink[];
  submitted_at: string | null;
  booking_requirements: BookingRequirementItem[];
  customer_requirements: CustomerRequirement[];
  attachments: ProjectAttachment[];
  timeline_events: BookingTimelineEvent[];
  notes: BookingNote[];
  developer_assignments: DeveloperAssignment[];
}

export interface CreateBookingInput {
  package: number;
  website_category: number;
  website_type?: number | null;
  website_name: string;
  business_name: string;
  business_type: BusinessType;
  description: string;
  preferred_delivery_date?: string | null;
  reference_links?: ReferenceLink[];
  required_feature_ids?: number[];
  custom_requirements?: { title: string; description?: string; priority?: string }[];
}