"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: passwordRules,
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export function ChangePasswordForm() {
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  async function onSubmit(values: FormValues) {
    setStatus("idle");
    try {
      await apiClient.post("/api/auth/change-password/", {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      setStatus("saved");
      reset();
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof ApiError ? err.body.detail ?? "Couldn't change your password." : "Couldn't change your password."
      );
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {status === "saved" && (
        <Alert variant="success">
          <AlertDescription>
            Password changed. You&apos;ll need to log in again on your other devices.
          </AlertDescription>
        </Alert>
      )}
      {status === "error" && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-2">
        <Label htmlFor="current_password">Current password</Label>
        <Input
          id="current_password"
          type="password"
          autoComplete="current-password"
          aria-invalid={!!errors.current_password}
          aria-describedby={errors.current_password ? "current_password-error" : undefined}
          {...register("current_password")}
        />
        {errors.current_password && (
          <p id="current_password-error" className="text-sm text-destructive">
            {errors.current_password.message}
          </p>
        )}
      </div>

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

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Changing…" : "Change password"}
      </Button>
    </form>
  );
}