import { FileText } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function SystemLogsPage() {
  return (
    <EmptyModulePlaceholder
      title="System Logs"
      description="Application-level logs for debugging and monitoring."
      icon={FileText}
    />
  );
}
