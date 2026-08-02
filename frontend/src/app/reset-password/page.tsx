"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/auth";

const passwordRules = z
  .string()
  .min(10, "At least 10 characters")
  .regex(/[A-Z]/, "One uppercase letter")
  .regex(/[a-z]/, "One lowercase letter")
  .regex(/\d/, "One digit")
  .regex(/[^A-Za-z0-9]/, "One special character");

const schema = z
  .object({ new_password: passwordRules, confirm_password: z.string() })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const uid = searchParams.get("uid");
  const token = searchParams.get("token");

  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: "", confirm_password: "" },
  });

  if (!uid || !token) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          This reset link is missing information. Request a new one from the{" "}
          <Link href="/forgot-password" className="underline">
            forgot password
          </Link>{" "}
          page.
        </AlertDescription>
      </Alert>
    );
  }

  async function onSubmit(values: FormValues) {
    setFormError(null);
    try {
      await apiClient.post(
        "/api/auth/reset-password/",
        { uid, token, new_password: values.new_password },
        { skipAuthRetry: true }
      );
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.body.detail ?? "This link is invalid or has expired.");
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  }

  if (success) {
    return (
      <Alert variant="success">
        <AlertDescription>Password reset. Redirecting you to log in…</AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && (
        <Alert variant="destructive">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
      <div className="space-y-2">
        <Label htmlFor="new_password">New password</Label>
        <Input
          id="new_password"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.new_password}
          aria-describedby={errors.new_password ? "new_password-error" : undefined}
          {...register("new_password")}
        />
        {errors.new_password && (
          <p id="new_password-error" className="text-sm text-destructive">
            {errors.new_password.message}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm_password">Confirm new password</Label>
        <Input
          id="confirm_password"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.confirm_password}
          aria-describedby={errors.confirm_password ? "confirm_password-error" : undefined}
          {...register("confirm_password")}
        />
        {errors.confirm_password && (
          <p id="confirm_password-error" className="text-sm text-destructive">
            {errors.confirm_password.message}
          </p>
        )}
      </div>
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Resetting…" : "Reset password"}
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Reset password</CardTitle>
          <CardDescription>Choose a new password for your account.</CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
            <ResetPasswordForm />
          </Suspense>
        </CardContent>
      </Card>
    </main>
  );
}