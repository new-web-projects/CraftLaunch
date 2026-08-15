"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Checkbox } from "@/components/ui/checkbox";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell } from "@/components/admin/settings-page-shell";
import type { AdminFeatureFlags } from "@/types/configuration";

interface FormValues {
  blog_enabled: boolean;
  booking_enabled: boolean;
  reviews_enabled: boolean;
  support_enabled: boolean;
  payments_enabled: boolean;
  registration_enabled: boolean;
  developer_signup_enabled: boolean;
  customer_signup_enabled: boolean;
  maintenance_mode: boolean;
}

const FLAGS: { key: keyof FormValues; label: string; hint: string }[] = [
  { key: "booking_enabled", label: "Bookings", hint: "The whole booking flow — creating and managing bookings." },
  { key: "blog_enabled", label: "Blog", hint: "Not built yet — reserved for a future part." },
  { key: "reviews_enabled", label: "Reviews", hint: "Not built yet — reserved for a future part." },
  { key: "support_enabled", label: "Support", hint: "Not built yet — reserved for a future part." },
  { key: "payments_enabled", label: "Payments", hint: "Configuration exists (Payment Settings); processing isn't built yet." },
  { key: "registration_enabled", label: "Registration", hint: "Whether new accounts can sign up at all." },
  { key: "developer_signup_enabled", label: "Developer signup", hint: "Registration must also be enabled." },
  { key: "customer_signup_enabled", label: "Customer signup", hint: "Registration must also be enabled." },
  { key: "maintenance_mode", label: "Maintenance mode", hint: "Shows a maintenance page to visitors on the public site." },
];

export default function FeatureFlagsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.featureFlags.get,
    configurationApi.featureFlags.update
  );

  const { register, handleSubmit, reset } = useForm<FormValues>();

  useEffect(() => {
    if (data) reset(data);
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    await save(values as Partial<AdminFeatureFlags>).catch(() => undefined);
  }

  return (
    <SettingsPageShell
      title="Feature Flags"
      description="Turn whole sections of the site on or off without a deployment."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
    >
      <div className="divide-y divide-border rounded-md border border-border">
        {FLAGS.map((flag) => (
          <div key={flag.key} className="flex items-start gap-3 p-3">
            <Checkbox id={flag.key} className="mt-0.5" {...register(flag.key)} />
            <label htmlFor={flag.key} className="flex-1 cursor-pointer">
              <span className="block text-sm font-medium text-foreground">{flag.label}</span>
              <span className="block text-xs text-muted-foreground">{flag.hint}</span>
            </label>
          </div>
        ))}
      </div>
    </SettingsPageShell>
  );
}
