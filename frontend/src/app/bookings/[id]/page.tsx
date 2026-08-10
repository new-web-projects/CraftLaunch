"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import { AttachmentList } from "@/components/bookings/attachment-list";
import { StatusBadge } from "@/components/bookings/status-badge";
import { Timeline } from "@/components/bookings/timeline";
import { useAuth } from "@/contexts/auth-context";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { bookingsApi } from "@/lib/bookings-api";
import { ApiError } from "@/types/auth";
import type { BookingDetail } from "@/types/bookings";

function formatDate(iso: string | null): string {
  if (!iso) return "Not set";
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

const CANCELLABLE_STATUSES = ["draft", "submitted", "accepted", "in_progress", "waiting_for_customer"];

function BookingDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();

  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  const load = useCallback(() => {
    bookingsApi
      .detail(params.id)
      .then((data) => {
        setBooking(data);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (status === "error") {
      router.replace("/unauthorized");
    }
  }, [status, router]);

  async function handleCancel() {
    if (!booking) return;
    if (!window.confirm("Cancel this booking? This can't be undone.")) return;
    setCancelError(null);
    setIsCancelling(true);
    try {
      const updated = await bookingsApi.cancel(booking.id);
      setBooking(updated);
    } catch (err) {
      setCancelError(err instanceof ApiError ? err.body.detail ?? "Couldn't cancel this booking." : "Couldn't cancel this booking.");
    } finally {
      setIsCancelling(false);
    }
  }

  if (status === "error") {
    return null;
  }

  if (status === "loading" || !booking) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-muted-foreground">Loading booking…</p>
      </main>
    );
  }

  const isOwner = user?.role === "CUSTOMER" && booking.status;
  const canCancel = isOwner && CANCELLABLE_STATUSES.includes(booking.status.code);
  const canModifyAttachments = !booking.status.is_terminal;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">{booking.website_name}</h1>
        <StatusBadge status={booking.status} />
      </div>
      <p className="mt-1 text-muted-foreground">
        {booking.package.name} · {booking.business_name}
      </p>

      {cancelError && (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{cancelError}</AlertDescription>
        </Alert>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Project details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <p className="text-foreground">{booking.description}</p>
              <Separator />
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">Website category</dt>
                  <dd className="text-foreground">{booking.website_category.name}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">Website type</dt>
                  <dd className="text-foreground">{booking.website_type?.name ?? "Not specified"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">Business type</dt>
                  <dd className="text-foreground">{booking.business_type.replace("_", " ").toLowerCase()}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">Preferred delivery</dt>
                  <dd className="text-foreground">{formatDate(booking.preferred_delivery_date)}</dd>
                </div>
              </dl>

              {booking.booking_requirements.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Required features</p>
                    <ul className="mt-1 flex flex-wrap gap-1.5">
                      {booking.booking_requirements.map((req) => (
                        <li
                          key={req.feature.id}
                          className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-secondary-foreground"
                        >
                          {req.feature.name}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}

              {booking.reference_links.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Reference links</p>
                    <ul className="mt-1 space-y-1">
                      {booking.reference_links.map((link, i) => (
                        <li key={i}>
                          <a
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary underline underline-offset-4"
                          >
                            {link.label || link.url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Files</CardTitle>
            </CardHeader>
            <CardContent>
              <AttachmentList
                bookingId={booking.id}
                attachments={booking.attachments}
                canModify={canModifyAttachments}
              />
            </CardContent>
          </Card>

          {booking.notes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {booking.notes.map((note) => (
                  <div key={note.id} className="rounded-md border border-border bg-card p-3 text-sm">
                    <p className="text-foreground">{note.content}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {note.author?.full_name || note.author?.username} · {formatDate(note.created_at)}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Timeline events={booking.timeline_events} />
            </CardContent>
          </Card>

          {canCancel && (
            <Button variant="destructive" className="w-full" onClick={handleCancel} disabled={isCancelling}>
              {isCancelling ? "Cancelling…" : "Cancel booking"}
            </Button>
          )}
        </div>
      </div>
    </main>
  );
}

export default function BookingDetailPage() {
  return (
    <RequireAuth>
      <BookingDetailContent />
    </RequireAuth>
  );
}