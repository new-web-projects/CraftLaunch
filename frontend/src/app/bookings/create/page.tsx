"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { RequireAuth } from "@/components/auth/require-auth";
import { RequireRole } from "@/components/auth/require-role";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { catalogApi } from "@/lib/catalog-api";
import { bookingsApi } from "@/lib/bookings-api";
import { generateIdempotencyKey } from "@/lib/idempotency";
import { ApiError } from "@/types/auth";
import type { PackageListItem, ServiceCategory, WebsiteCategory, WebsiteFeature, WebsiteType } from "@/types/catalog";
import type { BusinessType } from "@/types/bookings";

const BUSINESS_TYPES: { value: BusinessType; label: string }[] = [
  { value: "INDIVIDUAL", label: "Individual" },
  { value: "STARTUP", label: "Startup" },
  { value: "SMALL_BUSINESS", label: "Small business" },
  { value: "ENTERPRISE", label: "Enterprise" },
  { value: "NON_PROFIT", label: "Non-profit" },
  { value: "OTHER", label: "Other" },
];

// Mirrors bookings/validators.py exactly (name pattern, description
// length isn't validated server-side by length but a minimum here
// keeps low-effort submissions from reaching a developer unusable).
const nameSchema = z
  .string()
  .min(2, "Must be at least 2 characters")
  .regex(/^[\w][\w\s&.,'-]{1,148}[\w.,)]$/u, "Only letters, numbers, spaces and & . , ' - are allowed");

const bookingSchema = z.object({
  package: z.string().min(1, "Please select a package"),
  website_category: z.string().min(1, "Please select a category"),
  website_type: z.string().optional(),
  website_name: nameSchema,
  business_name: nameSchema,
  business_type: z.enum(["INDIVIDUAL", "STARTUP", "SMALL_BUSINESS", "ENTERPRISE", "NON_PROFIT", "OTHER"], {
    message: "Please select a business type",
  }),
  description: z.string().min(20, "Please describe your project in at least 20 characters"),
  preferred_delivery_date: z.string().optional(),
  reference_links: z.array(z.object({ label: z.string().optional(), url: z.string().url("Enter a valid URL") })),
  required_feature_ids: z.array(z.string()).optional(),
});

type BookingForm = z.infer<typeof bookingSchema>;

function CreateBookingFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedPackageId = searchParams.get("package");

  const [packages, setPackages] = useState<PackageListItem[]>([]);
  const [serviceCategories, setServiceCategories] = useState<ServiceCategory[]>([]);
  const [websiteCategories, setWebsiteCategories] = useState<WebsiteCategory[]>([]);
  const [websiteTypes, setWebsiteTypes] = useState<WebsiteType[]>([]);
  const [features, setFeatures] = useState<WebsiteFeature[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const idempotencyKey = useMemo(() => generateIdempotencyKey(), []);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<BookingForm>({
    resolver: zodResolver(bookingSchema),
    defaultValues: {
      package: preselectedPackageId ?? "",
      reference_links: [],
      required_feature_ids: [],
    },
  });

  const { fields: linkFields, append: appendLink, remove: removeLink } = useFieldArray({
    control,
    name: "reference_links",
  });

  useEffect(() => {
    catalogApi.packages().then((res) => setPackages(res.results)).catch(() => setPackages([]));
    catalogApi.serviceCategories().then(setServiceCategories).catch(() => setServiceCategories([]));
    catalogApi.websiteCategories().then(setWebsiteCategories).catch(() => setWebsiteCategories([]));
    catalogApi.websiteTypes().then(setWebsiteTypes).catch(() => setWebsiteTypes([]));
    catalogApi.websiteFeatures().then(setFeatures).catch(() => setFeatures([]));
  }, []);

  async function onSubmit(values: BookingForm) {
    setFormError(null);
    setIsSubmitting(true);
    try {
      const booking = await bookingsApi.create(
        {
          package: Number(values.package),
          website_category: Number(values.website_category),
          website_type: values.website_type ? Number(values.website_type) : null,
          website_name: values.website_name,
          business_name: values.business_name,
          business_type: values.business_type,
          description: values.description,
          preferred_delivery_date: values.preferred_delivery_date || null,
          reference_links: values.reference_links.filter((l) => l.url),
          required_feature_ids: (values.required_feature_ids ?? []).map(Number),
        },
        idempotencyKey
      );
      router.push(`/bookings/${booking.id}/success`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.body.detail ?? "Couldn't submit your booking. Please try again." : "Couldn't submit your booking. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const minDeliveryDate = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 3);
    return d.toISOString().split("T")[0];
  }, []);

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-3xl font-semibold tracking-tight text-foreground">Create a booking</h1>
      <p className="mt-1 text-muted-foreground">Tell us about your project and we&apos;ll get started.</p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-6">
        {formError && (
          <Alert variant="destructive">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Package &amp; category</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="package">Package</Label>
              <Select
                id="package"
                aria-invalid={!!errors.package}
                aria-describedby={errors.package ? "package-error" : undefined}
                {...register("package")}
              >
                <option value="">Select a package…</option>
                {serviceCategories.map((category) => (
                  <optgroup key={category.id} label={category.name}>
                    {packages
                      .filter((p) => p.service_category.id === category.id)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} — ${p.starting_price}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </Select>
              {errors.package && (
                <p id="package-error" className="text-sm text-destructive">
                  {errors.package.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="website_category">Website category</Label>
                <Select
                  id="website_category"
                  aria-invalid={!!errors.website_category}
                  aria-describedby={errors.website_category ? "website_category-error" : undefined}
                  {...register("website_category")}
                >
                  <option value="">Select…</option>
                  {websiteCategories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
                {errors.website_category && (
                  <p id="website_category-error" className="text-sm text-destructive">
                    {errors.website_category.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="website_type">Website type (optional)</Label>
                <Select id="website_type" {...register("website_type")}>
                  <option value="">Select…</option>
                  {websiteTypes.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Project details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="website_name">Website name</Label>
                <Input
                  id="website_name"
                  aria-invalid={!!errors.website_name}
                  aria-describedby={errors.website_name ? "website_name-error" : undefined}
                  {...register("website_name")}
                />
                {errors.website_name && (
                  <p id="website_name-error" className="text-sm text-destructive">
                    {errors.website_name.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="business_name">Business name</Label>
                <Input
                  id="business_name"
                  aria-invalid={!!errors.business_name}
                  aria-describedby={errors.business_name ? "business_name-error" : undefined}
                  {...register("business_name")}
                />
                {errors.business_name && (
                  <p id="business_name-error" className="text-sm text-destructive">
                    {errors.business_name.message}
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="business_type">Business type</Label>
              <Select
                id="business_type"
                aria-invalid={!!errors.business_type}
                aria-describedby={errors.business_type ? "business_type-error" : undefined}
                {...register("business_type")}
              >
                <option value="">Select…</option>
                {BUSINESS_TYPES.map((bt) => (
                  <option key={bt.value} value={bt.value}>
                    {bt.label}
                  </option>
                ))}
              </Select>
              {errors.business_type && (
                <p id="business_type-error" className="text-sm text-destructive">
                  {errors.business_type.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Project description</Label>
              <Textarea
                id="description"
                rows={5}
                aria-invalid={!!errors.description}
                aria-describedby={errors.description ? "description-error" : undefined}
                {...register("description")}
              />
              {errors.description && (
                <p id="description-error" className="text-sm text-destructive">
                  {errors.description.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="preferred_delivery_date">Preferred delivery date (optional)</Label>
              <Input
                id="preferred_delivery_date"
                type="date"
                min={minDeliveryDate}
                {...register("preferred_delivery_date")}
              />
              <p className="text-xs text-muted-foreground">At least 3 days from today.</p>
            </div>
          </CardContent>
        </Card>

        {features.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Required features</CardTitle>
              <CardDescription>Select anything you know you&apos;ll need.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {features.map((feature) => (
                  <label key={feature.id} className="flex items-center gap-2 text-sm text-foreground">
                    <Checkbox value={feature.id} {...register("required_feature_ids")} />
                    {feature.name}
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Reference links</CardTitle>
            <CardDescription>Sites or designs you&apos;d like us to draw inspiration from.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {linkFields.map((field, index) => (
              <div key={field.id} className="flex gap-2">
                <Input placeholder="Label (optional)" className="w-1/3" {...register(`reference_links.${index}.label`)} />
                <Input
                  placeholder="https://…"
                  className="flex-1"
                  aria-invalid={!!errors.reference_links?.[index]?.url}
                  {...register(`reference_links.${index}.url`)}
                />
                <Button type="button" variant="ghost" size="icon" aria-label="Remove link" onClick={() => removeLink(index)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={() => appendLink({ label: "", url: "" })}>
              <Plus className="h-4 w-4" />
              Add a link
            </Button>
          </CardContent>
        </Card>

        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Submitting…" : "Submit booking"}
        </Button>
        <p className="text-center text-xs text-muted-foreground">
          File uploads happen on the next screen, once your booking has been created.
        </p>
      </form>
    </main>
  );
}

export default function CreateBookingPage() {
  return (
    <RequireAuth>
      <RequireRole roles={["CUSTOMER"]}>
        <CreateBookingFormContent />
      </RequireRole>
    </RequireAuth>
  );
}