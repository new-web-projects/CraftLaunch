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
import { countryOptions, languageOptions, timezoneOptions } from "@/lib/locale-data";
import { useAuth } from "@/contexts/auth-context";
import type { AuthUser } from "@/types/auth";

const schema = z.object({
  first_name: z.string().max(150).optional(),
  last_name: z.string().max(150).optional(),
  profile_picture_url: z.union([z.string().url(), z.literal("")]).optional(),
  phone: z.string().max(32).optional(),
  country: z.string().max(2).optional(),
  timezone: z.string().max(64).optional(),
  language: z.string().max(8).optional(),
});

type FormValues = z.infer<typeof schema>;

export function ProfileDetailsForm({ user }: { user: AuthUser }) {
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: user.first_name,
      last_name: user.last_name,
      profile_picture_url: user.profile.profile_picture_url,
      phone: user.profile.phone,
      country: user.profile.country,
      timezone: user.profile.timezone,
      language: user.profile.language,
    },
  });

  async function onSubmit(values: FormValues) {
    setStatus("idle");
    try {
      await apiClient.patch("/api/auth/me/", values);
      await refreshUser();
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {status === "saved" && (
        <Alert variant="success">
          <AlertDescription>Profile updated.</AlertDescription>
        </Alert>
      )}
      {status === "error" && (
        <Alert variant="destructive">
          <AlertDescription>Couldn&apos;t save your changes. Please try again.</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="first_name">First name</Label>
          <Input id="first_name" {...register("first_name")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last name</Label>
          <Input id="last_name" {...register("last_name")} />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="profile_picture_url">Profile picture URL</Label>
        <Input id="profile_picture_url" placeholder="https://…" {...register("profile_picture_url")} />
        <p className="text-xs text-muted-foreground">
          Direct upload arrives once file storage (S3/Cloudinary) is wired up in a later part —
          paste a URL for now.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="phone">Phone</Label>
        <Input id="phone" type="tel" {...register("phone")} />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="country">Country</Label>
          <select
            id="country"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...register("country")}
          >
            <option value="">—</option>
            {countryOptions().map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="timezone">Timezone</Label>
          <select
            id="timezone"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...register("timezone")}
          >
            {timezoneOptions().map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="language">Language</Label>
          <select
            id="language"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            {...register("language")}
          >
            {languageOptions().map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Button type="submit" disabled={isSubmitting || !isDirty}>
        {isSubmitting ? "Saving…" : "Save changes"}
      </Button>
    </form>
  );
}