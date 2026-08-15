import { CalendarClock } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function BookingSettingsPage() {
  return (
    <EmptyModulePlaceholder
      title="Booking Settings"
      description="Booking workflow defaults, statuses, and assignment rules."
      icon={CalendarClock}
    />
  );
}
