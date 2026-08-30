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

export const MILESTONE_STAGES = [
  "REQUIREMENTS",
  "PLANNING",
  "DESIGN",
  "DEVELOPMENT",
  "TESTING",
  "DELIVERY",
] as const;

export type MilestoneStage = (typeof MILESTONE_STAGES)[number];

export interface ProjectMilestone {
  id: number;
  stage: MilestoneStage;
  stage_display: string;
  sort_order: number;
  is_completed: boolean;
  completed_at: string | null;
  completed_by: BookingActor | null;
}

export interface ProjectDelivery {
  notes: string;
  final_url: string;
  access_instructions: string;
  files: ProjectAttachment[];
  delivered_by: BookingActor | null;
  delivered_at: string | null;
  accepted_at: string | null;
}

export interface SubmitDeliveryInput {
  notes?: string;
  final_url?: string;
  access_instructions?: string;
  attachment_ids?: string[];
}

export type RevisionStatus = "PENDING" | "ACKNOWLEDGED" | "LIMIT_EXCEEDED";

export interface RevisionRequest {
  id: number;
  reason: string;
  description: string;
  attachment: ProjectAttachment | null;
  status: RevisionStatus;
  status_display: string;
  requested_by: BookingActor | null;
  created_at: string;
}

export interface CreateRevisionInput {
  reason: string;
  description?: string;
  attachment_id?: string | null;
}

export interface NotificationEvent {
  id: number;
  event_type: string;
  event_type_display: string;
  message: string;
  booking_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface RecentActivityEvent {
  id: number;
  event_type: string;
  event_type_display: string;
  actor: BookingActor | null;
  description: string;
  booking_id: string;
  website_name: string;
  created_at: string;
}

export interface CustomerDashboardData {
  counts: {
    active_projects: number;
    pending_bookings: number;
    completed_projects: number;
    cancelled_projects: number;
    awaiting_your_action: number;
  };
  recently_updated: BookingListItem[];
  recent_activity: RecentActivityEvent[];
}

export interface DeveloperDashboardData {
  counts: {
    new_project_requests: number;
    accepted_projects: number;
    active_projects: number;
    waiting_for_customer: number;
    ready_for_delivery: number;
    completed_projects: number;
    cancelled_projects: number;
  };
  upcoming_deadlines: BookingListItem[];
  recent_activity: RecentActivityEvent[];
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
  progress_percent: number;
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
  milestones: ProjectMilestone[];
  delivery: ProjectDelivery | null;
  revision_requests: RevisionRequest[];
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