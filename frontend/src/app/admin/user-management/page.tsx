import { Users } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function UserManagementPage() {
  return (
    <EmptyModulePlaceholder
      title="User Management"
      description="Search, view, and manage every account on the platform."
      icon={Users}
    />
  );
}
