"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, BellOff } from "lucide-react";

import { bookingsApi } from "@/lib/bookings-api";
import { ApiError } from "@/types/auth";
import type { NotificationEvent } from "@/types/bookings";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { cn } from "@/lib/utils";

function timeAgo(isoDate: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
  const units: [number, string][] = [
    [31536000, "y"], [2592000, "mo"], [86400, "d"], [3600, "h"], [60, "m"],
  ];
  for (const [secondsInUnit, label] of units) {
    const count = Math.floor(seconds / secondsInUnit);
    if (count >= 1) return `${count}${label} ago`;
  }
  return "just now";
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setNotifications(null);
    bookingsApi
      .notifications()
      .then((res) => setNotifications(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load notifications."));
  };

  useEffect(() => {
    bookingsApi
      .notifications()
      .then((res) => setNotifications(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load notifications."));
  }, []);

  const markRead = async (notification: NotificationEvent) => {
    if (notification.is_read) return;
    // Optimistic — this is a low-stakes, easily-reversible toggle, so
    // update the list immediately rather than waiting on the round trip.
    setNotifications((prev) =>
      prev ? prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n)) : prev
    );
    try {
      await bookingsApi.markNotificationRead(notification.id);
    } catch {
      load();
    }
  };

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!notifications) return <LoadingState label="Loading notifications…" />;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Notifications</h1>
        <p className="text-muted-foreground">
          {unreadCount > 0 ? `${unreadCount} unread` : "You're all caught up."}
        </p>
      </div>

      {notifications.length === 0 ? (
        <EmptyState icon={BellOff} title="No notifications yet" description="Updates on your projects will appear here." />
      ) : (
        <div className="space-y-2">
          {notifications.map((notification) => {
            const content = (
              <Card
                className={cn(
                  "flex items-start gap-3 p-4 transition-colors",
                  !notification.is_read && "border-primary/40 bg-primary/5"
                )}
              >
                <Bell className={cn("mt-0.5 h-4 w-4 shrink-0", !notification.is_read ? "text-primary" : "text-muted-foreground")} />
                <div className="min-w-0 flex-1">
                  <p className={cn("text-sm", !notification.is_read ? "font-medium text-foreground" : "text-foreground")}>
                    {notification.message}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{timeAgo(notification.created_at)}</p>
                </div>
                {!notification.is_read && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />}
              </Card>
            );

            return notification.booking_id ? (
              <Link
                key={notification.id}
                href={`/bookings/${notification.booking_id}`}
                onClick={() => markRead(notification)}
                className="block"
              >
                {content}
              </Link>
            ) : (
              <button key={notification.id} type="button" onClick={() => markRead(notification)} className="block w-full text-left">
                {content}
              </button>
            );
          })}
        </div>
      )}

      {unreadCount > 0 && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            notifications.filter((n) => !n.is_read).forEach(markRead);
          }}
        >
          Mark all as read
        </Button>
      )}
    </div>
  );
}