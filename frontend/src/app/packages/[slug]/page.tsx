"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { Check, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { catalogApi } from "@/lib/catalog-api";
import type { PackageDetail } from "@/types/catalog";

export default function PackageDetailPage() {
  const params = useParams<{ slug: string }>();
  const [pkg, setPkg] = useState<PackageDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "not-found">("loading");

  useEffect(() => {
    catalogApi
      .packageDetail(params.slug)
      .then((data) => {
        setPkg(data);
        setStatus("ready");
      })
      .catch(() => setStatus("not-found"));
  }, [params.slug]);

  if (status === "not-found") {
    notFound();
  }

  if (status === "loading" || !pkg) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-muted-foreground">Loading package…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="mb-6 flex items-center justify-between">
        <Badge variant="secondary">{pkg.tier_display}</Badge>
        <Link href="/packages" className="text-sm text-muted-foreground hover:text-foreground">
          ← All packages
        </Link>
      </div>

      <h1 className="text-3xl font-semibold tracking-tight text-foreground">{pkg.name}</h1>
      <p className="mt-2 text-muted-foreground">{pkg.description}</p>

      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Starting at</p>
            <p className="text-2xl font-semibold text-foreground">${pkg.starting_price}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Delivery</p>
            <p className="text-2xl font-semibold text-foreground">{pkg.delivery_days} days</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Revisions</p>
            <p className="text-2xl font-semibold text-foreground">{pkg.revision_count}</p>
          </CardContent>
        </Card>
      </div>

      {pkg.package_features.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>What&apos;s included</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {pkg.package_features.map((pf) => (
                <li key={pf.feature.id} className="flex items-center gap-2 text-sm text-foreground">
                  {pf.is_highlighted ? (
                    <Star className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  ) : (
                    <Check className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  )}
                  {pf.feature.name}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {pkg.technologies.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-1.5">
          {pkg.technologies.map((tech) => (
            <Badge key={tech.id} variant="outline">
              {tech.name}
            </Badge>
          ))}
        </div>
      )}

      <div className="mt-8">
        <Button asChild size="lg" className="w-full sm:w-auto">
          <Link href={`/bookings/create?package=${pkg.id}`}>Book this package</Link>
        </Button>
        <p className="mt-2 text-xs text-muted-foreground">
          {pkg.support_duration_days} days of support included after delivery.
        </p>
      </div>
    </main>
  );
}