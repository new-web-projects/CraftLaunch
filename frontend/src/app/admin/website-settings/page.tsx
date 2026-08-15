"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid } from "@/components/admin/settings-page-shell";
import type { AdminSiteConfig } from "@/types/configuration";

const schema = z.object({
  website_name: z.string().min(1, "Website name is required").max(100),
  tagline: z.string().max(255).optional(),
  description: z.string().optional(),
  contact_email: z.string().email("Enter a valid email").or(z.literal("")).optional(),
  support_email: z.string().email("Enter a valid email").or(z.literal("")).optional(),
  support_phone: z.string().max(30).optional(),
  business_address: z.string().optional(),
  copyright_text: z.string().max(255).optional(),
  footer_text: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function WebsiteSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.site.get,
    configurationApi.site.update
  );

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (data) reset(data);
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    await save(values as Partial<AdminSiteConfig>).catch(() => undefined);
  }

  return (
    <SettingsPageShell
      title="Website Settings"
      description="Your site's name, tagline, and how customers reach you."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
    >
      <FieldGrid>
        <Field label="Website name" htmlFor="website_name">
          <Input id="website_name" {...register("website_name")} />
          {errors.website_name && <p className="text-xs text-destructive">{errors.website_name.message}</p>}
        </Field>
        <Field label="Tagline" htmlFor="tagline">
          <Input id="tagline" {...register("tagline")} />
        </Field>
      </FieldGrid>

      <Field label="Description" htmlFor="description" hint="Shown in the site footer and used as a fallback meta description.">
        <Textarea id="description" rows={3} {...register("description")} />
      </Field>

      <FieldGrid>
        <Field label="Contact email" htmlFor="contact_email">
          <Input id="contact_email" type="email" {...register("contact_email")} />
          {errors.contact_email && <p className="text-xs text-destructive">{errors.contact_email.message}</p>}
        </Field>
        <Field label="Support email" htmlFor="support_email">
          <Input id="support_email" type="email" {...register("support_email")} />
          {errors.support_email && <p className="text-xs text-destructive">{errors.support_email.message}</p>}
        </Field>
      </FieldGrid>

      <FieldGrid>
        <Field label="Support phone" htmlFor="support_phone">
          <Input id="support_phone" {...register("support_phone")} />
        </Field>
        <Field label="Copyright text" htmlFor="copyright_text" hint="e.g. © 2026 CraftLaunch">
          <Input id="copyright_text" {...register("copyright_text")} />
        </Field>
      </FieldGrid>

      <Field label="Business address" htmlFor="business_address">
        <Textarea id="business_address" rows={2} {...register("business_address")} />
      </Field>

      <Field label="Footer text" htmlFor="footer_text">
        <Textarea id="footer_text" rows={2} {...register("footer_text")} />
      </Field>
    </SettingsPageShell>
  );
}
