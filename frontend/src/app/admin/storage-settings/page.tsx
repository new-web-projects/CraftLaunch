"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid, SectionHeading } from "@/components/admin/settings-page-shell";
import type { AdminStorageConfig } from "@/types/configuration";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

interface FormValues {
  active_provider: string;
  s3_enabled: boolean;
  cloudinary_enabled: boolean;
  s3_access_key_id: string;
  s3_secret_access_key: string;
  s3_bucket_name: string;
  s3_region: string;
  cloudinary_cloud_name: string;
  cloudinary_api_key: string;
  cloudinary_api_secret: string;
}

export default function StorageSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.storage.get,
    configurationApi.storage.update
  );

  const { register, handleSubmit, reset } = useForm<FormValues>();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; detail: string } | null>(null);

  useEffect(() => {
    if (data) {
      reset({
        active_provider: data.active_provider,
        s3_enabled: data.s3_enabled,
        cloudinary_enabled: data.cloudinary_enabled,
        s3_access_key_id: data.s3_access_key_id,
        s3_secret_access_key: "",
        s3_bucket_name: data.s3_bucket_name,
        s3_region: data.s3_region,
        cloudinary_cloud_name: data.cloudinary_cloud_name,
        cloudinary_api_key: data.cloudinary_api_key,
        cloudinary_api_secret: "",
      });
    }
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    setTestResult(null);
    await save(values as Partial<AdminStorageConfig>).catch(() => undefined);
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await configurationApi.testStorageConnection();
      setTestResult(result);
    } catch {
      setTestResult({ success: false, detail: "Test request failed." });
    } finally {
      setTesting(false);
    }
  }

  return (
    <SettingsPageShell
      title="Storage Settings"
      description="Where uploaded files (attachments, logos) are stored — switch providers without a deployment."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
      extraActions={
        <Button type="button" variant="outline" onClick={handleTest} disabled={testing}>
          {testing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Test Connection
        </Button>
      }
    >
      {testResult && (
        <div
          className={
            "flex items-center gap-2 rounded-md border px-3 py-2 text-sm " +
            (testResult.success
              ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
              : "border-destructive/30 bg-destructive/10 text-destructive")
          }
        >
          {testResult.success ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          {testResult.detail}
        </div>
      )}

      <Field label="Active provider" htmlFor="active_provider" hint="Which provider new uploads use. Save credentials for a provider before switching to it.">
        <Select id="active_provider" {...register("active_provider")}>
          <option value="LOCAL">Local disk</option>
          <option value="S3">Amazon S3</option>
          <option value="CLOUDINARY">Cloudinary</option>
        </Select>
      </Field>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Checkbox id="s3_enabled" {...register("s3_enabled")} />
          <label htmlFor="s3_enabled" className="text-sm font-medium text-foreground">Enable Amazon S3</label>
        </div>
        <SectionHeading>Amazon S3</SectionHeading>
        <FieldGrid>
          <Field label="Access key ID" htmlFor="s3_access_key_id">
            <Input id="s3_access_key_id" {...register("s3_access_key_id")} />
          </Field>
          <Field
            label="Secret access key"
            htmlFor="s3_secret_access_key"
            hint={data?.s3_secret_access_key_is_set ? "Configured — leave blank to keep it." : "Not set."}
          >
            <Input id="s3_secret_access_key" type="password" placeholder="••••••••" {...register("s3_secret_access_key")} />
          </Field>
        </FieldGrid>
        <FieldGrid>
          <Field label="Bucket name" htmlFor="s3_bucket_name">
            <Input id="s3_bucket_name" {...register("s3_bucket_name")} />
          </Field>
          <Field label="Region" htmlFor="s3_region" hint="e.g. ap-south-1">
            <Input id="s3_region" {...register("s3_region")} />
          </Field>
        </FieldGrid>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Checkbox id="cloudinary_enabled" {...register("cloudinary_enabled")} />
          <label htmlFor="cloudinary_enabled" className="text-sm font-medium text-foreground">Enable Cloudinary</label>
        </div>
        <SectionHeading>Cloudinary</SectionHeading>
        <FieldGrid>
          <Field label="Cloud name" htmlFor="cloudinary_cloud_name">
            <Input id="cloudinary_cloud_name" {...register("cloudinary_cloud_name")} />
          </Field>
          <Field label="API key" htmlFor="cloudinary_api_key">
            <Input id="cloudinary_api_key" {...register("cloudinary_api_key")} />
          </Field>
        </FieldGrid>
        <Field
          label="API secret"
          htmlFor="cloudinary_api_secret"
          hint={data?.cloudinary_api_secret_is_set ? "Configured — leave blank to keep it." : "Not set."}
        >
          <Input id="cloudinary_api_secret" type="password" placeholder="••••••••" className="max-w-sm" {...register("cloudinary_api_secret")} />
        </Field>
      </div>
    </SettingsPageShell>
  );
}
