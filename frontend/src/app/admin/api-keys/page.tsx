import { KeyRound } from "lucide-react";
import { EmptyModulePlaceholder } from "@/components/admin/empty-module-placeholder";

export default function ApiKeysPage() {
  return (
    <EmptyModulePlaceholder
      title="API Keys"
      description="Issue and revoke API keys for external integrations."
      icon={KeyRound}
    />
  );
}
