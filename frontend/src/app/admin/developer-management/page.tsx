import { Wrench } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function DeveloperManagementPage() {
  return (
    <EmptyModulePlaceholder
      title="Developer Management"
      description="Manage developer accounts, assignments, and availability."
      icon={Wrench}
    />
  );
}
