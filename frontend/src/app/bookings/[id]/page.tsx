"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import { AttachmentList } from "@/components/bookings/attachment-list";
import { DeliveryPanel } from "@/components/bookings/delivery-panel";
import { MilestoneList } from "@/components/bookings/milestone-list";
import { NotesPanel } from "@/components/bookings/notes-panel";
import { RequirementsPanel } from "@/components/bookings/requirements-panel";
import { RevisionPanel } from "@/components/bookings/revision-panel";
import { StatusBadge } from "@/components/bookings/status-badge";
import { Timeline } from "@/components/bookings/timeline";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { useAuth } from "@/contexts/auth-context";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { bookingsApi } from "@/lib/bookings-api";
import { ApiError } from "@/types/auth";
import type { BookingDetail, CreateRevisionInput, SubmitDeliveryInput } from "@/types/bookings";

function formatDate(iso: string | null): string {
  if (!iso) return "Not set";
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

function computeExpectedDelivery(startedAt: string | null, deliveryDays: number): string | null {
  if (!startedAt) return null;
  const date = new Date(startedAt);
  date.setDate(date.getDate() + deliveryDays);
  return date.toISOString();
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

// Every non-terminal status except "delivered" — see
// apps/bookings/lifecycle.py's TRANSITIONS graph: once delivered, the
// only forward moves are accepting it or requesting a revision, not
// cancelling outright.
const CANCELLABLE_STATUSES = [
  "draft", "submitted", "awaiting_developer", "accepted",
  "in_progress", "waiting_for_customer", "revision_requested", "ready_for_delivery",
];

function BookingDetailContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();

  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [actionError, setActionError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [devActionPending, setDevActionPending] = useState<string | null>(null);

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

  async function handleCancel(reason?: string) {
    if (!booking) return;
    setActionError(null);
    setIsCancelling(true);
    try {
      const updated = await bookingsApi.cancel(booking.id, reason);
      setBooking(updated);
      setCancelDialogOpen(false);
    } catch (err) {
      setActionError(errorMessage(err, "Couldn't cancel this booking."));
    } finally {
      setIsCancelling(false);
    }
  }

  async function handleDevAction(action: "start" | "mark-waiting" | "mark-ready") {
    if (!booking) return;
    setActionError(null);
    setDevActionPending(action);
    try {
      const updated = await (action === "start"
        ? bookingsApi.start(booking.id)
        : action === "mark-waiting"
          ? bookingsApi.markWaitingForCustomer(booking.id)
          : bookingsApi.markReady(booking.id));
      setBooking(updated);
    } catch (err) {
      setActionError(errorMessage(err, "That action couldn't be completed."));
    } finally {
      setDevActionPending(null);
    }
  }

  async function handleMilestoneToggle(milestoneId: number, isCompleted: boolean) {
    if (!booking) return;
    try {
      await bookingsApi.updateMilestone(booking.id, milestoneId, isCompleted);
      load();
    } catch (err) {
      setActionError(errorMessage(err, "Couldn't update that milestone."));
    }
  }

  async function handleSubmitDelivery(input: SubmitDeliveryInput) {
    if (!booking) return;
    await bookingsApi.submitDelivery(booking.id, input);
    load();
  }

  async function handleAcceptDelivery() {
    if (!booking) return;
    const updated = await bookingsApi.acceptDelivery(booking.id);
    setBooking(updated);
  }

  async function handleRequestRevision(input: CreateRevisionInput) {
    if (!booking) return;
    await bookingsApi.requestRevision(booking.id, input);
    load();
  }

  async function handleAddNote(content: string) {
    if (!booking) return;
    await bookingsApi.addNote(booking.id, content);
    load();
  }

  async function handleAddRequirement(title: string) {
    if (!booking) return;
    await bookingsApi.addRequirement(booking.id, { title });
    load();
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

  const isOwner = user?.role === "CUSTOMER" && Boolean(booking.status);
  const isAssignedDeveloper =
    user?.role === "DEVELOPER" &&
    booking.developer_assignments.some((a) => a.developer.id === user.id && a.is_active);
  const isAdmin = user?.role === "ADMIN";
  const canActAsDeveloper = isAssignedDeveloper || isAdmin;
  const activeAssignment = booking.developer_assignments.find((a) => a.is_active) ?? null;
  const canCancel = isOwner && CANCELLABLE_STATUSES.includes(booking.status.code);
  const canModifyAttachments = !booking.status.is_terminal;
  const showLifecyclePanels = booking.milestones.length > 0; // i.e. accepted or further along
  const showRevisionRequest = ["waiting_for_customer", "delivered"].includes(booking.status.code);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">{booking.website_name}</h1>
        <StatusBadge status={booking.status} />
      </div>
      <p className="mt-1 text-muted-foreground">
        {booking.package.name} · {booking.business_name}
      </p>

      {actionError && (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {canActAsDeveloper && (
            <Card>
              <CardHeader>
                <CardTitle>Project Actions</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {booking.status.code === "accepted" && (
                  <Button size="sm" onClick={() => handleDevAction("start")} disabled={devActionPending !== null}>
                    {devActionPending === "start" ? "Starting…" : "Start Project"}
                  </Button>
                )}
                {booking.status.code === "in_progress" && (
                  <Button size="sm" variant="outline" onClick={() => handleDevAction("mark-waiting")} disabled={devActionPending !== null}>
                    {devActionPending === "mark-waiting" ? "Updating…" : "Mark Waiting on Customer"}
                  </Button>
                )}
                {booking.status.code === "waiting_for_customer" && (
                  <Button size="sm" variant="outline" onClick={() => handleDevAction("mark-ready")} disabled={devActionPending !== null}>
                    {devActionPending === "mark-ready" ? "Updating…" : "Mark Ready for Delivery"}
                  </Button>
                )}
                {!["accepted", "in_progress", "waiting_for_customer"].includes(booking.status.code) && (
                  <p className="text-sm text-muted-foreground">No actions available at this stage.</p>
                )}
              </CardContent>
            </Card>
          )}

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
                {activeAssignment && (
                  <>
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-muted-foreground">Start date</dt>
                      <dd className="text-foreground">{formatDate(activeAssignment.assigned_at)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-muted-foreground">Expected delivery</dt>
                      <dd className="text-foreground">
                        {formatDate(computeExpectedDelivery(activeAssignment.assigned_at, booking.package.delivery_days))}
                      </dd>
                    </div>
                  </>
                )}
              </dl>

              {activeAssignment && (
                <>
                  <Separator />
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">Assigned developer</p>
                    <p className="mt-1 text-foreground">
                      {activeAssignment.developer.full_name || activeAssignment.developer.username}
                    </p>
                  </div>
                </>
              )}

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

          {showLifecyclePanels && (
            <Card>
              <CardHeader>
                <CardTitle>Milestones</CardTitle>
              </CardHeader>
              <CardContent>
                <MilestoneList
                  bookingId={booking.id}
                  milestones={booking.milestones}
                  progressPercent={booking.progress_percent}
                  canEdit={canActAsDeveloper}
                  onToggle={handleMilestoneToggle}
                />
              </CardContent>
            </Card>
          )}

          {showLifecyclePanels && (
            <Card>
              <CardHeader>
                <CardTitle>Delivery</CardTitle>
              </CardHeader>
              <CardContent>
                <DeliveryPanel
                  booking={booking}
                  canDeliver={canActAsDeveloper}
                  canAcceptOrRevise={Boolean(isOwner) || isAdmin}
                  onSubmitDelivery={handleSubmitDelivery}
                  onAcceptDelivery={handleAcceptDelivery}
                  onRequestRevisionClick={() => document.getElementById("revision-panel")?.scrollIntoView({ behavior: "smooth" })}
                />
              </CardContent>
            </Card>
          )}

          {showLifecyclePanels && (
            <Card id="revision-panel">
              <CardHeader>
                <CardTitle>Revisions</CardTitle>
              </CardHeader>
              <CardContent>
                <RevisionPanel
                  revisions={booking.revision_requests}
                  revisionsIncluded={booking.package.revision_count}
                  canRequest={(Boolean(isOwner) || isAdmin) && showRevisionRequest}
                  onRequestRevision={handleRequestRevision}
                />
              </CardContent>
            </Card>
          )}

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

          <Card>
            <CardHeader>
              <CardTitle>Additional Requirements</CardTitle>
            </CardHeader>
            <CardContent>
              <RequirementsPanel
                requirements={booking.customer_requirements}
                canAdd={(Boolean(isOwner) || isAdmin) && !booking.status.is_terminal}
                onAddRequirement={handleAddRequirement}
              />
            </CardContent>
          </Card>

          {booking.notes.length > 0 || !booking.status.is_terminal ? (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <NotesPanel notes={booking.notes} onAddNote={handleAddNote} />
              </CardContent>
            </Card>
          ) : null}
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
            <Button variant="destructive" className="w-full" onClick={() => setCancelDialogOpen(true)} disabled={isCancelling}>
              {isCancelling ? "Cancelling…" : "Cancel booking"}
            </Button>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
        title="Cancel this booking?"
        description="This can't be undone. Let us know why you're cancelling."
        confirmLabel="Cancel booking"
        variant="destructive"
        requireReason
        reasonLabel="Cancellation reason"
        onConfirm={handleCancel}
        isLoading={isCancelling}
      />
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