"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Input } from "@/components/ui/input";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid, SectionHeading } from "@/components/admin/settings-page-shell";
import { AssetUploadField } from "@/components/admin/asset-upload-field";
import type { AdminSiteConfig } from "@/types/configuration";

const hexColor = z
  .string()
  .regex(/^#[0-9A-Fa-f]{6}$/, "Use a 6-digit hex color, e.g. #D97706");

const schema = z.object({
  primary_color: hexColor,
  secondary_color: hexColor,
  accent_color: hexColor,
});

type FormValues = z.infer<typeof schema>;

export default function BrandSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload, setSaved } = useAdminSettings(
    configurationApi.site.get,
    configurationApi.site.update
  );

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  // Uploaded assets persist immediately server-side (SiteAssetUploadView
  // saves on upload, not on this form's Save) — this only tracks
  // optimistic preview updates right after a successful upload, set
  // from that upload's own callback (an event handler, not an
  // effect), never synced from `data` directly.
  const [uploadedUrls, setUploadedUrls] = useState<Record<string, string>>({});

  function assetUrl(key: string, fallback: string) {
    return uploadedUrls[key] ?? fallback;
  }

  useEffect(() => {
    if (data) {
      reset({
        primary_color: data.primary_color,
        secondary_color: data.secondary_color,
        accent_color: data.accent_color,
      });
    }
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    await save(values as Partial<AdminSiteConfig>).catch(() => undefined);
  }

  return (
    <SettingsPageShell
      title="Brand Settings"
      description="Logos, favicon, and the colors that theme the site."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
    >
      <div className="space-y-4">
        <SectionHeading>Logos</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <AssetUploadField
            label="Logo"
            asset="logo"
            currentUrl={assetUrl("logo", data?.logo_url ?? "")}
            onUploaded={(url) => { setUploadedUrls((prev) => ({ ...prev, logo: url })); setSaved(true); }}
          />
          <AssetUploadField
            label="Favicon"
            asset="favicon"
            currentUrl={assetUrl("favicon", data?.favicon_url ?? "")}
            onUploaded={(url) => { setUploadedUrls((prev) => ({ ...prev, favicon: url })); setSaved(true); }}
          />
          <AssetUploadField
            label="Footer logo"
            asset="footer-logo"
            currentUrl={assetUrl("footer-logo", data?.footer_logo_url ?? "")}
            onUploaded={(url) => { setUploadedUrls((prev) => ({ ...prev, "footer-logo": url })); setSaved(true); }}
          />
          <AssetUploadField
            label="Light-mode logo"
            asset="light-logo"
            currentUrl={assetUrl("light-logo", data?.light_logo_url ?? "")}
            onUploaded={(url) => { setUploadedUrls((prev) => ({ ...prev, "light-logo": url })); setSaved(true); }}
          />
          <AssetUploadField
            label="Dark-mode logo"
            asset="dark-logo"
            currentUrl={assetUrl("dark-logo", data?.dark_logo_url ?? "")}
            onUploaded={(url) => { setUploadedUrls((prev) => ({ ...prev, "dark-logo": url })); setSaved(true); }}
          />
        </div>
      </div>

      <div className="space-y-4">
        <SectionHeading>Colors</SectionHeading>
        <FieldGrid>
          <Field label="Primary color" htmlFor="primary_color">
            <div className="flex items-center gap-2">
              <input type="color" className="h-9 w-10 rounded border border-border" {...register("primary_color")} />
              <Input id="primary_color" {...register("primary_color")} />
            </div>
            {errors.primary_color && <p className="text-xs text-destructive">{errors.primary_color.message}</p>}
          </Field>
          <Field label="Secondary color" htmlFor="secondary_color">
            <div className="flex items-center gap-2">
              <input type="color" className="h-9 w-10 rounded border border-border" {...register("secondary_color")} />
              <Input id="secondary_color" {...register("secondary_color")} />
            </div>
            {errors.secondary_color && <p className="text-xs text-destructive">{errors.secondary_color.message}</p>}
          </Field>
        </FieldGrid>
        <Field label="Accent color" htmlFor="accent_color">
          <div className="flex items-center gap-2">
            <input type="color" className="h-9 w-10 rounded border border-border" {...register("accent_color")} />
            <Input id="accent_color" className="max-w-xs" {...register("accent_color")} />
          </div>
          {errors.accent_color && <p className="text-xs text-destructive">{errors.accent_color.message}</p>}
        </Field>
        <p className="text-xs text-muted-foreground">
          Changing these values here updates the stored configuration; applying them to the live
          site theme is a follow-up piece (see docs/ARCHITECTURE.md).
        </p>
      </div>
    </SettingsPageShell>
  );
}
