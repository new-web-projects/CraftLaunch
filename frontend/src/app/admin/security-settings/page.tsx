import { Lock } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function SecuritySettingsPage() {
  return (
    <EmptyModulePlaceholder
      title="Security Settings"
      description="Rate limits, IP rules, and account-protection controls."
      icon={Lock}
    />
  );
}
