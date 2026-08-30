import type { LucideIcon } from "lucide-react";
import {
  Bell,
  Briefcase,
  CheckCircle2,
  ClipboardList,
  FolderKanban,
  Inbox,
  LayoutDashboard,
  PlusCircle,
  Settings,
  User,
} from "lucide-react";

export interface DashboardNavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

// Consolidation notes (kept here rather than duplicated as comments
// on every href below): the spec lists "Profile" and "Settings" as
// separate nav entries for both roles, but /profile already covers
// account details, password, sessions, and account deletion — exactly
// what a "Settings" page would otherwise hold, so both entries point
// there rather than existing as a near-duplicate empty page. Likewise
// "My Bookings" and "My Projects" both resolve through the same
// /bookings list (a booking *is* the project record end to end in
// this codebase — see docs/ARCHITECTURE.md's own ProjectStatus/
// ProjectAttachment naming) — "My Projects" pre-applies a status
// filter for the customer so the two links are meaningfully
// different in what they show, not just in name.
export const CUSTOMER_NAV: DashboardNavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "My Bookings", href: "/bookings", icon: ClipboardList },
  {
    label: "My Projects",
    href: "/bookings?status=accepted,in_progress,waiting_for_customer,revision_requested,ready_for_delivery,delivered,completed",
    icon: FolderKanban,
  },
  { label: "New Booking", href: "/packages", icon: PlusCircle },
  { label: "Profile", href: "/profile", icon: User },
  { label: "Notifications", href: "/dashboard/notifications", icon: Bell },
  { label: "Settings", href: "/profile", icon: Settings },
];

export const DEVELOPER_NAV: DashboardNavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Project Requests", href: "/dashboard/requests", icon: Inbox },
  { label: "My Projects", href: "/bookings", icon: FolderKanban },
  { label: "Active Projects", href: "/bookings?status=in_progress", icon: Briefcase },
  { label: "Completed Projects", href: "/bookings?status=completed", icon: CheckCircle2 },
  { label: "Profile", href: "/profile", icon: User },
  { label: "Notifications", href: "/dashboard/notifications", icon: Bell },
  { label: "Settings", href: "/profile", icon: Settings },
];