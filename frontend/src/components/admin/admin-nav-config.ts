import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Globe,
  Palette,
  Settings,
  Search,
  ToggleLeft,
  Database,
  CreditCard,
  Mail,
  ShieldCheck,
  Lock,
  KeyRound,
  Package,
  CalendarClock,
  Users,
  Wrench,
  UserCog,
  FileText,
  ClipboardList,
  AlertTriangle,
} from "lucide-react";

export interface AdminNavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Modules with real forms today vs. the Part 4 "empty production-ready
   * module" placeholders — drives the badge shown in the sidebar, not
   * access control (permission protection is the same for every /admin
   * route, via RequireRole in admin/layout.tsx). */
  status: "live" | "planned";
}

export interface AdminNavGroup {
  label: string;
  items: AdminNavItem[];
}

export const ADMIN_NAV: AdminNavGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/admin", icon: LayoutDashboard, status: "live" }],
  },
  {
    label: "Site Configuration",
    items: [
      { label: "Website Settings", href: "/admin/website-settings", icon: Globe, status: "live" },
      { label: "Brand Settings", href: "/admin/brand-settings", icon: Palette, status: "live" },
      { label: "General Settings", href: "/admin/general-settings", icon: Settings, status: "live" },
      { label: "SEO Settings", href: "/admin/seo-settings", icon: Search, status: "live" },
      { label: "Feature Flags", href: "/admin/feature-flags", icon: ToggleLeft, status: "live" },
    ],
  },
  {
    label: "Integrations",
    items: [
      { label: "Storage Settings", href: "/admin/storage-settings", icon: Database, status: "live" },
      { label: "Payment Settings", href: "/admin/payment-settings", icon: CreditCard, status: "live" },
      { label: "Email Settings", href: "/admin/email-settings", icon: Mail, status: "live" },
    ],
  },
  {
    label: "Access & Security",
    items: [
      { label: "Authentication Settings", href: "/admin/authentication-settings", icon: ShieldCheck, status: "planned" },
      { label: "Security Settings", href: "/admin/security-settings", icon: Lock, status: "planned" },
      { label: "API Keys", href: "/admin/api-keys", icon: KeyRound, status: "planned" },
    ],
  },
  {
    label: "Catalog & Bookings",
    items: [
      { label: "Package Settings", href: "/admin/package-settings", icon: Package, status: "planned" },
      { label: "Booking Settings", href: "/admin/booking-settings", icon: CalendarClock, status: "planned" },
    ],
  },
  {
    label: "People",
    items: [
      { label: "User Management", href: "/admin/user-management", icon: Users, status: "planned" },
      { label: "Developer Management", href: "/admin/developer-management", icon: Wrench, status: "planned" },
      { label: "Customer Management", href: "/admin/customer-management", icon: UserCog, status: "planned" },
    ],
  },
  {
    label: "Monitoring",
    items: [
      { label: "System Logs", href: "/admin/system-logs", icon: FileText, status: "planned" },
      { label: "Audit Logs", href: "/admin/audit-logs", icon: ClipboardList, status: "planned" },
    ],
  },
  {
    label: "System",
    items: [
      { label: "Maintenance Mode", href: "/admin/maintenance-mode", icon: AlertTriangle, status: "planned" },
    ],
  },
];

export const ADMIN_NAV_FLAT: AdminNavItem[] = ADMIN_NAV.flatMap((group) => group.items);

export function findAdminNavItem(pathname: string): AdminNavItem | undefined {
  return ADMIN_NAV_FLAT.find((item) => item.href === pathname);
}
