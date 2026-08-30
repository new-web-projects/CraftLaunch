"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Calendar, Inbox } from "lucide-react";

import { bookingsApi } from "@/lib/bookings-api";
import { ApiError } from "@/types/auth";
import type { BookingDetail } from "@/types/bookings";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";

export default function ProjectRequestsPage() {
  const [requests, setRequests] = useState<BookingDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actingOn, setActingOn] = useState<BookingDetail | null>(null);
  const [dialogMode, setDialogMode] = useState<"accept" | "reject" | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setRequests(null);
    bookingsApi
      .requests()
      .then((res) => setRequests(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load project requests."));
  };

  useEffect(() => {
    bookingsApi
      .requests()
      .then((res) => setRequests(res.results))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load project requests."));
  }, []);

  const openDialog = (booking: BookingDetail, mode: "accept" | "reject") => {
    setActingOn(booking);
    setDialogMode(mode);
    setActionError(null);
  };

  const closeDialog = () => {
    setActingOn(null);
    setDialogMode(null);
  };

  const handleConfirm = async (reason?: string) => {
    if (!actingOn || !dialogMode) return;
    setSubmitting(true);
    setActionError(null);
    try {
      if (dialogMode === "accept") {
        await bookingsApi.accept(actingOn.id);
      } else {
        await bookingsApi.reject(actingOn.id, reason ?? "");
      }
      closeDialog();
      load();
    } catch (err) {
      setActionError(
        err instanceof ApiError
          ? err.message
          : `Couldn't ${dialogMode} this project. It may have just been taken by another developer.`
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!requests) return <LoadingState label="Loading open project requests…" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Project Requests</h1>
        <p className="text-muted-foreground">
          Open requests any developer can pick up. Once you accept one, it moves to your active projects.
        </p>
      </div>

      {requests.length === 0 ? (
        <EmptyState icon={Inbox} title="No open requests right now" description="Check back soon — new bookings show up here as customers submit them." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {requests.map((booking) => (
            <Card key={booking.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{booking.website_name}</CardTitle>
                  <Badge variant="outline">{booking.package.name}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="line-clamp-3 text-sm text-muted-foreground">{booking.description}</p>
                <dl className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Website type</dt>
                    <dd className="text-foreground">{booking.website_type?.name ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Business type</dt>
                    <dd className="text-foreground">{booking.business_type}</dd>
                  </div>
                </dl>
                {booking.booking_requirements.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {booking.booking_requirements.map((req) => (
                      <Badge key={req.feature.id} variant="secondary" className="text-xs">
                        {req.feature.name}
                      </Badge>
                    ))}
                  </div>
                )}
                {booking.preferred_delivery_date && (
                  <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Calendar className="h-3.5 w-3.5" />
                    Requested delivery: {new Date(booking.preferred_delivery_date).toLocaleDateString()}
                  </p>
                )}
                {booking.attachments.length > 0 && (
                  <p className="text-sm text-muted-foreground">
                    {booking.attachments.length} attachment{booking.attachments.length === 1 ? "" : "s"}
                  </p>
                )}
                <div className="flex items-center gap-2 pt-2">
                  <Button size="sm" onClick={() => openDialog(booking, "accept")}>
                    Accept
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => openDialog(booking, "reject")}>
                    Reject
                  </Button>
                  <Button size="sm" variant="ghost" asChild className="ml-auto">
                    <Link href={`/bookings/${booking.id}`}>View details</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {actingOn && (
        <ConfirmDialog
          open={dialogMode !== null}
          onOpenChange={(open) => !open && closeDialog()}
          title={dialogMode === "accept" ? "Accept this project?" : "Reject this project?"}
          description={
            dialogMode === "accept"
              ? `You'll be assigned to "${actingOn.website_name}" and it will move to your active projects.`
              : `Let the customer know why "${actingOn.website_name}" isn't a fit right now.`
          }
          confirmLabel={dialogMode === "accept" ? "Accept project" : "Reject project"}
          variant={dialogMode === "reject" ? "destructive" : "default"}
          requireReason={dialogMode === "reject"}
          reasonLabel="Rejection reason"
          reasonPlaceholder="e.g. Outside my area of expertise, timeline doesn't work, …"
          onConfirm={handleConfirm}
          isLoading={submitting}
        />
      )}
      {actionError && <ErrorState message={actionError} />}
    </div>
  );
}