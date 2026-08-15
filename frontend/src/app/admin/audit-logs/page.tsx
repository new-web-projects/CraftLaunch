import { ClipboardList } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function AuditLogsPage() {
  return (
    <EmptyModulePlaceholder
      title="Audit Logs"
      description="A record of every admin action taken on the platform."
      icon={ClipboardList}
    />
  );
}
