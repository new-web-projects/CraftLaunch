"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid, SectionHeading } from "@/components/admin/settings-page-shell";
import type { AdminSEOConfig } from "@/types/configuration";

const schema = z.object({
  site_title: z.string().max(255).optional(),
  meta_description: z.string().max(500).optional(),
  meta_keywords: z.string().max(500).optional(),
  canonical_url: z.string().url("Enter a valid URL").or(z.literal("")).optional(),
  robots_directive: z.string().max(100).optional(),
  google_verification: z.string().max(255).optional(),
  bing_verification: z.string().max(255).optional(),
  og_title: z.string().max(255).optional(),
  og_description: z.string().max(500).optional(),
  facebook_domain_verification: z.string().max(255).optional(),
  twitter_site: z.string().max(100).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function SEOSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.seo.get,
    configurationApi.seo.update
  );

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (data) reset(data);
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    await save(values as Partial<AdminSEOConfig>).catch(() => undefined);
  }

  return (
    <SettingsPageShell
      title="SEO Settings"
      description="Default meta tags used across the site unless a page sets its own."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
    >
      <div className="space-y-4">
        <SectionHeading>Meta tags</SectionHeading>
        <Field label="Site title" htmlFor="site_title">
          <Input id="site_title" {...register("site_title")} />
        </Field>
        <Field label="Meta description" htmlFor="meta_description">
          <Textarea id="meta_description" rows={2} {...register("meta_description")} />
        </Field>
        <Field label="Meta keywords" htmlFor="meta_keywords" hint="Comma-separated.">
          <Input id="meta_keywords" {...register("meta_keywords")} />
        </Field>
        <FieldGrid>
          <Field label="Canonical URL" htmlFor="canonical_url">
            <Input id="canonical_url" {...register("canonical_url")} />
            {errors.canonical_url && <p className="text-xs text-destructive">{errors.canonical_url.message}</p>}
          </Field>
          <Field label="Robots directive" htmlFor="robots_directive">
            <Input id="robots_directive" {...register("robots_directive")} />
          </Field>
        </FieldGrid>
      </div>

      <div className="space-y-4">
        <SectionHeading>Search console verification</SectionHeading>
        <FieldGrid>
          <Field label="Google verification" htmlFor="google_verification">
            <Input id="google_verification" {...register("google_verification")} />
          </Field>
          <Field label="Bing verification" htmlFor="bing_verification">
            <Input id="bing_verification" {...register("bing_verification")} />
          </Field>
        </FieldGrid>
      </div>

      <div className="space-y-4">
        <SectionHeading>Social sharing</SectionHeading>
        <FieldGrid>
          <Field label="Open Graph title" htmlFor="og_title">
            <Input id="og_title" {...register("og_title")} />
          </Field>
          <Field label="Twitter/X @handle" htmlFor="twitter_site">
            <Input id="twitter_site" placeholder="@craftlaunch" {...register("twitter_site")} />
          </Field>
        </FieldGrid>
        <Field label="Open Graph description" htmlFor="og_description">
          <Textarea id="og_description" rows={2} {...register("og_description")} />
        </Field>
        <Field label="Facebook domain verification" htmlFor="facebook_domain_verification">
          <Input id="facebook_domain_verification" {...register("facebook_domain_verification")} />
        </Field>
      </div>
    </SettingsPageShell>
  );
}
