"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import type { Session } from "@/types/auth";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function ActiveSessions() {
  const { logoutAll } = useAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiClient
      .get<Session[]>("/api/auth/sessions/")
      .then(setSessions)
      .catch(() => setError("Couldn't load your active sessions."));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function revoke(id: number) {
    try {
      await apiClient.delete(`/api/auth/sessions/${id}/`);
      setSessions((prev) => prev?.filter((s) => s.id !== id) ?? null);
    } catch {
      setError("Couldn't revoke that session.");
    }
  }

  async function handleLogoutAll() {
    await logoutAll();
    router.push("/login");
  }

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {sessions === null ? (
        <p className="text-sm text-muted-foreground">Loading sessions…</p>
      ) : sessions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No other active sessions.</p>
      ) : (
        <ul className="space-y-2">
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex items-center justify-between gap-4 rounded-md border border-border p-3 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate text-foreground">
                  {session.user_agent || "Unknown device"}
                  {session.is_current && (
                    <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                      This device
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  {session.ip_address ?? "Unknown IP"} · last active {formatDate(session.last_seen_at)}
                </p>
              </div>
              {!session.is_current && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => revoke(session.id)}
                  aria-label={`Revoke session on ${session.user_agent || "unknown device"}`}
                >
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      <Button variant="destructive" onClick={handleLogoutAll}>
        Log out of all devices
      </Button>
    </div>
  );
}