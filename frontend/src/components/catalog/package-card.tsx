import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import type { PackageListItem } from "@/types/catalog";

export function PackageCard({ pkg }: { pkg: PackageListItem }) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <Badge variant="secondary">{pkg.tier_display}</Badge>
          <span className="text-xs text-muted-foreground">{pkg.service_category.name}</span>
        </div>
        <CardTitle className="mt-2">{pkg.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 space-y-3">
        <p className="text-2xl font-semibold text-foreground">
          from ${pkg.starting_price}
        </p>
        <dl className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
          <div>
            <dt className="text-xs uppercase tracking-wide">Delivery</dt>
            <dd>{pkg.delivery_days} days</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide">Revisions</dt>
            <dd>{pkg.revision_count}</dd>
          </div>
        </dl>
        {pkg.technologies.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {pkg.technologies.map((tech) => (
              <Badge key={tech.id} variant="outline">
                {tech.name}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
      <CardFooter>
        <Button asChild className="w-full">
          <Link href={`/packages/${pkg.slug}`}>View details</Link>
        </Button>
      </CardFooter>
    </Card>
  );
}