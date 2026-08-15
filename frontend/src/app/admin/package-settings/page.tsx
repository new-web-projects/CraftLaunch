import { Package } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function PackageSettingsPage() {
  return (
    <EmptyModulePlaceholder
      title="Package Settings"
      description="Defaults and rules for the service package catalog."
      icon={Package}
    />
  );
}
