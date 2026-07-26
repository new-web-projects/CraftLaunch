"use client";

import { useEffect, useState } from "react";
import type { HealthCheckResponse } from "@/types";

type Status = "checking" | "online" | "offline";

/**
 * Dev/ops utility, not a product feature. Pings the Django health
 * check endpoint on mount so anyone running both dev servers gets an
 * immediate, visible signal that the API URL, CORS and both servers
 * are wired together correctly — a quick real-world extension of the
 * "Build Verification" step for this part.
 */
export function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [detail, setDetail] = useState<string>("Checking API…");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    fetch(`${apiUrl}/api/health/`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HealthCheckResponse>;
      })
      .then((data) => {
        setStatus("online");
        setDetail(`API online — ${data.service} v${data.version}`);
      })
      .catch(() => {
        setStatus("offline");
        setDetail(
          "API unreachable. Start the Django dev server and confirm NEXT_PUBLIC_API_URL."
        );
      })
      .finally(() => clearTimeout(timeout));

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, []);

  const dotClass =
    status === "online"
      ? "bg-emerald-500"
      : status === "offline"
        ? "bg-destructive"
        : "bg-muted-foreground animate-pulse";

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-sm text-card-foreground">
      <span className={`h-2 w-2 rounded-full ${dotClass}`} aria-hidden="true" />
      <span>{detail}</span>
    </div>
  );
}
