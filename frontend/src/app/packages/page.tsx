"use client";

import { useEffect, useState } from "react";

import { PackageCard } from "@/components/catalog/package-card";
import { Select } from "@/components/ui/select";
import { catalogApi } from "@/lib/catalog-api";
import type { PackageListItem, ServiceCategory } from "@/types/catalog";

export default function PackagesPage() {
  const [packages, setPackages] = useState<PackageListItem[]>([]);
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Mirrors the pattern already used in app/bookings/page.tsx: no
    // synchronous setState in the effect body itself — isLoading
    // already starts true, and every setState call below happens
    // inside a .then()/.catch()/.finally() callback, not the effect
    // body directly.
    catalogApi.serviceCategories().then(setCategories).catch(() => setCategories([]));
    catalogApi
      .packages()
      .then((res) => setPackages(res.results))
      .catch(() => setPackages([]))
      .finally(() => setIsLoading(false));
  }, []);

  function handleCategoryChange(categoryId: string) {
    setSelectedCategory(categoryId);
    setIsLoading(true);
    catalogApi
      .packages(categoryId ? { service_category: Number(categoryId) } : undefined)
      .then((res) => setPackages(res.results))
      .catch(() => setPackages([]))
      .finally(() => setIsLoading(false));
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Packages</h1>
          <p className="mt-1 text-muted-foreground">
            Pick a package to get started — every tier includes a fixed delivery timeline and revision count.
          </p>
        </div>
        <div className="w-full sm:w-56">
          <Select
            aria-label="Filter by service category"
            value={selectedCategory}
            onChange={(e) => handleCategoryChange(e.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading packages…</p>
      ) : packages.length === 0 ? (
        <p className="text-muted-foreground">No packages found for this category yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {packages.map((pkg) => (
            <PackageCard key={pkg.id} pkg={pkg} />
          ))}
        </div>
      )}
    </main>
  );
}