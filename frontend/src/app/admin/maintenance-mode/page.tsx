import { AlertTriangle } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function MaintenanceModePage() {
  return (
    <EmptyModulePlaceholder
      title="Maintenance Mode"
      description="Take the public site offline for planned maintenance."
      icon={AlertTriangle}
    />
  );
}
