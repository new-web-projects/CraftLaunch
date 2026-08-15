"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid } from "@/components/admin/settings-page-shell";
import type { AdminEmailConfig } from "@/types/configuration";

interface FormValues {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  sender_name: string;
  sender_email: string;
  reply_email: string;
  use_tls: boolean;
  use_ssl: boolean;
}

export default function EmailSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.email.get,
    configurationApi.email.update
  );

  const { register, handleSubmit, reset } = useForm<FormValues>();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; detail: string } | null>(null);

  useEffect(() => {
    if (data) {
      reset({
        smtp_host: data.smtp_host,
        smtp_port: data.smtp_port,
        smtp_username: data.smtp_username,
        smtp_password: "",
        sender_name: data.sender_name,
        sender_email: data.sender_email,
        reply_email: data.reply_email,
        use_tls: data.use_tls,
        use_ssl: data.use_ssl,
      });
    }
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    setTestResult(null);
    await save({ ...values, smtp_port: Number(values.smtp_port) } as Partial<AdminEmailConfig>).catch(() => undefined);
  }

  async function runTest(sendTestEmail: boolean) {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await configurationApi.testEmailConnection(sendTestEmail);
      setTestResult(result);
    } catch {
      setTestResult({ success: false, detail: "Test request failed." });
    } finally {
      setTesting(false);
    }
  }

  return (
    <SettingsPageShell
      title="Email Settings"
      description="SMTP delivery for verification, password-reset, and notification emails."
      status={status}
      saving={saving}
      saved={saved}
      saveError={saveError}
      onRetry={reload}
      onSubmit={handleSubmit(onSubmit)}
      extraActions={
        <>
          <Button type="button" variant="outline" onClick={() => runTest(false)} disabled={testing}>
            {testing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Test Connection
          </Button>
          <Button type="button" variant="outline" onClick={() => runTest(true)} disabled={testing}>
            Send Test Email
          </Button>
        </>
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

      <FieldGrid>
        <Field label="SMTP host" htmlFor="smtp_host">
          <Input id="smtp_host" {...register("smtp_host")} />
        </Field>
        <Field label="SMTP port" htmlFor="smtp_port">
          <Input id="smtp_port" type="number" {...register("smtp_port")} />
        </Field>
      </FieldGrid>

      <FieldGrid>
        <Field label="SMTP username" htmlFor="smtp_username">
          <Input id="smtp_username" {...register("smtp_username")} />
        </Field>
        <Field
          label="SMTP password"
          htmlFor="smtp_password"
          hint={data?.smtp_password_is_set ? "Configured — leave blank to keep it." : "Not set."}
        >
          <Input id="smtp_password" type="password" placeholder="••••••••" {...register("smtp_password")} />
        </Field>
      </FieldGrid>

      <FieldGrid>
        <Field label="Sender name" htmlFor="sender_name">
          <Input id="sender_name" {...register("sender_name")} />
        </Field>
        <Field label="Sender email" htmlFor="sender_email">
          <Input id="sender_email" type="email" {...register("sender_email")} />
        </Field>
      </FieldGrid>

      <Field label="Reply-to email" htmlFor="reply_email">
        <Input id="reply_email" type="email" className="max-w-sm" {...register("reply_email")} />
      </Field>

      <div className="flex gap-6">
        <div className="flex items-center gap-2">
          <Checkbox id="use_tls" {...register("use_tls")} />
          <label htmlFor="use_tls" className="text-sm font-medium text-foreground">Use TLS</label>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox id="use_ssl" {...register("use_ssl")} />
          <label htmlFor="use_ssl" className="text-sm font-medium text-foreground">Use SSL</label>
        </div>
      </div>
    </SettingsPageShell>
  );
}
