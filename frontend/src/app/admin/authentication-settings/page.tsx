import { ShieldCheck } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function AuthenticationSettingsPage() {
  return (
    <EmptyModulePlaceholder
      title="Authentication Settings"
      description="Password policy, session lifetimes, and login rules."
      icon={ShieldCheck}
    />
  );
}
