"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { useAdminSettings } from "@/lib/use-admin-settings";
import { configurationApi } from "@/lib/configuration-api";
import { SettingsPageShell, Field, FieldGrid } from "@/components/admin/settings-page-shell";
import type { AdminPaymentConfig } from "@/types/configuration";

interface FormValues {
  razorpay_key_id: string;
  razorpay_key_secret: string;
  razorpay_webhook_secret: string;
  default_currency: string;
  mode: string;
  is_enabled: boolean;
}

export default function PaymentSettingsPage() {
  const { data, status, saving, saveError, saved, save, reload } = useAdminSettings(
    configurationApi.payment.get,
    configurationApi.payment.update
  );

  const { register, handleSubmit, reset } = useForm<FormValues>();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; detail: string } | null>(null);

  useEffect(() => {
    if (data) {
      reset({
        razorpay_key_id: data.razorpay_key_id,
        razorpay_key_secret: "",
        razorpay_webhook_secret: "",
        default_currency: data.default_currency,
        mode: data.mode,
        is_enabled: data.is_enabled,
      });
    }
  }, [data, reset]);

  async function onSubmit(values: FormValues) {
    setTestResult(null);
    await save(values as Partial<AdminPaymentConfig>).catch(() => undefined);
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await configurationApi.testPaymentConnection();
      setTestResult(result);
    } catch {
      setTestResult({ success: false, detail: "Test request failed." });
    } finally {
      setTesting(false);
    }
  }

  return (
    <SettingsPageShell
      title="Payment Settings"
      description="Razorpay configuration. This saves and validates credentials only — payments aren't processed yet."
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

      <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/50 p-3">
        <Checkbox id="is_enabled" {...register("is_enabled")} />
        <label htmlFor="is_enabled" className="text-sm font-medium text-foreground">
          Enable payments
        </label>
        <span className="ml-auto text-xs text-muted-foreground">Configuration only — no charges are processed by this build.</span>
      </div>

      <FieldGrid>
        <Field label="Key ID" htmlFor="razorpay_key_id">
          <Input id="razorpay_key_id" {...register("razorpay_key_id")} />
        </Field>
        <Field label="Mode" htmlFor="mode">
          <Select id="mode" {...register("mode")}>
            <option value="SANDBOX">Sandbox</option>
            <option value="LIVE">Live</option>
          </Select>
        </Field>
      </FieldGrid>

      <FieldGrid>
        <Field
          label="Key secret"
          htmlFor="razorpay_key_secret"
          hint={data?.razorpay_key_secret_is_set ? "Configured — leave blank to keep it." : "Not set."}
        >
          <Input id="razorpay_key_secret" type="password" placeholder="••••••••" {...register("razorpay_key_secret")} />
        </Field>
        <Field
          label="Webhook secret"
          htmlFor="razorpay_webhook_secret"
          hint={data?.razorpay_webhook_secret_is_set ? "Configured — leave blank to keep it." : "Not set."}
        >
          <Input id="razorpay_webhook_secret" type="password" placeholder="••••••••" {...register("razorpay_webhook_secret")} />
        </Field>
      </FieldGrid>

      <Field label="Default currency" htmlFor="default_currency">
        <Input id="default_currency" className="max-w-[8rem]" {...register("default_currency")} />
      </Field>
    </SettingsPageShell>
  );
}
