import { UserCog } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function CustomerManagementPage() {
  return (
    <EmptyModulePlaceholder
      title="Customer Management"
      description="View customer accounts and their booking history."
      icon={UserCog}
    />
  );
}
