"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid } from "@/components/admin/settings-page-shell";
import type { AdminSiteConfig } from "@/types/configuration";

const schema = z.object({
  default_language: z.string().min(2).max(10),
  timezone: z.string().min(1).max(64),
  date_format: z.string().min(1).max(20),
  currency: z.string().length(3, "Use a 3-letter code, e.g. INR"),
});

type FormValues = z.infer<typeof schema>;

const DATE_FORMATS = ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"];
const CURRENCIES = ["INR", "USD", "EUR", "GBP", "AUD", "CAD"];
const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "bn", label: "Bengali" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
];

export default function GeneralSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.site.get,
    configurationApi.site.update
  );

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (data) {
      reset({
        default_language: data.default_language,
        timezone: data.timezone,
        date_format: data.date_format,
        currency: data.currency,
      });
    }
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    await save(values as Partial<AdminSiteConfig>).catch(() => undefined);
  }

  return (
    <SettingsPageShell
      title="General Settings"
      description="Language, timezone, date format, and currency defaults."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
    >
      <FieldGrid>
        <Field label="Default language" htmlFor="default_language">
          <Select id="default_language" {...register("default_language")}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>{l.label}</option>
            ))}
          </Select>
        </Field>
        <Field label="Currency" htmlFor="currency">
          <Select id="currency" {...register("currency")}>
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </Select>
          {errors.currency && <p className="text-xs text-destructive">{errors.currency.message}</p>}
        </Field>
      </FieldGrid>

      <FieldGrid>
        <Field label="Timezone" htmlFor="timezone" hint="IANA timezone name, e.g. Asia/Kolkata or UTC.">
          <Input id="timezone" {...register("timezone")} />
          {errors.timezone && <p className="text-xs text-destructive">{errors.timezone.message}</p>}
        </Field>
        <Field label="Date format" htmlFor="date_format">
          <Select id="date_format" {...register("date_format")}>
            {DATE_FORMATS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </Select>
        </Field>
      </FieldGrid>
    </SettingsPageShell>
  );
}
