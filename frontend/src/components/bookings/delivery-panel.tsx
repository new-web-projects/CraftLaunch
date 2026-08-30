"use client";

import { useState } from "react";
import { ExternalLink, PackageCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/shared/states";
import type { BookingDetail, SubmitDeliveryInput } from "@/types/bookings";

const DELIVERABLE_STATUSES = new Set(["waiting_for_customer", "ready_for_delivery"]);

interface DeliveryPanelProps {
  booking: BookingDetail;
  canDeliver: boolean;
  canAcceptOrRevise: boolean;
  onSubmitDelivery: (input: SubmitDeliveryInput) => Promise<void>;
  onAcceptDelivery: () => Promise<void>;
  onRequestRevisionClick: () => void;
}

export function DeliveryPanel({
  booking,
  canDeliver,
  canAcceptOrRevise,
  onSubmitDelivery,
  onAcceptDelivery,
  onRequestRevisionClick,
}: DeliveryPanelProps) {
  const [notes, setNotes] = useState("");
  const [finalUrl, setFinalUrl] = useState("");
  const [accessInstructions, setAccessInstructions] = useState("");
  const [selectedAttachmentIds, setSelectedAttachmentIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const showSubmitForm = canDeliver && DELIVERABLE_STATUSES.has(booking.status.code);

  const toggleAttachment = (id: string) => {
    setSelectedAttachmentIds((prev) => (prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onSubmitDelivery({
        notes,
        final_url: finalUrl,
        access_instructions: accessInstructions,
        attachment_ids: selectedAttachmentIds,
      });
      setNotes("");
      setFinalUrl("");
      setAccessInstructions("");
      setSelectedAttachmentIds([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't submit the delivery.");
    } finally {
      setSubmitting(false);
    }
  };

  const [accepting, setAccepting] = useState(false);
  const handleAccept = async () => {
    setAccepting(true);
    setError(null);
    try {
      await onAcceptDelivery();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't accept the delivery.");
    } finally {
      setAccepting(false);
    }
  };

  return (
    <div className="space-y-4">
      {booking.delivery ? (
        <div className="space-y-3 rounded-md border border-border p-4">
          <div className="flex items-center justify-between">
            <p className="font-medium text-foreground">Delivery</p>
            {booking.delivery.accepted_at ? (
              <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">Accepted</Badge>
            ) : (
              <Badge variant="outline">Awaiting review</Badge>
            )}
          </div>
          {booking.delivery.notes && <p className="text-sm text-muted-foreground">{booking.delivery.notes}</p>}
          {booking.delivery.final_url && (
            <a
              href={booking.delivery.final_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              {booking.delivery.final_url} <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {booking.delivery.access_instructions && (
            <div>
              <p className="text-xs font-medium text-muted-foreground">Access instructions</p>
              <p className="whitespace-pre-wrap text-sm text-foreground">{booking.delivery.access_instructions}</p>
            </div>
          )}
          {booking.delivery.files.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {booking.delivery.files.map((file) => (
                <Badge key={file.id} variant="secondary" className="text-xs">
                  {file.original_filename}
                </Badge>
              ))}
            </div>
          )}

          {canAcceptOrRevise && !booking.delivery.accepted_at && (
            <div className="flex gap-2 pt-2">
              <Button size="sm" onClick={handleAccept} disabled={accepting}>
                {accepting ? "Accepting…" : "Accept Delivery"}
              </Button>
              <Button size="sm" variant="outline" onClick={onRequestRevisionClick}>
                Request Revision
              </Button>
            </div>
          )}
        </div>
      ) : (
        !showSubmitForm && (
          <EmptyState icon={PackageCheck} title="No delivery yet" description="The developer hasn't submitted a delivery for this project yet." />
        )
      )}

      {showSubmitForm && (
        <div className="space-y-3 rounded-md border border-dashed border-border p-4">
          <p className="font-medium text-foreground">
            {booking.delivery ? "Submit a new delivery" : "Submit delivery"}
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="delivery-notes">Delivery notes</Label>
            <Textarea id="delivery-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="What's included in this delivery…" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="delivery-url">Final website URL</Label>
            <Input id="delivery-url" type="url" value={finalUrl} onChange={(e) => setFinalUrl(e.target.value)} placeholder="https://…" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="delivery-access">Access instructions</Label>
            <Textarea
              id="delivery-access"
              rows={2}
              value={accessInstructions}
              onChange={(e) => setAccessInstructions(e.target.value)}
              placeholder="Login details, hosting notes, anything the customer needs…"
            />
          </div>
          {booking.attachments.length > 0 && (
            <div className="space-y-1.5">
              <Label>Include uploaded files</Label>
              <div className="space-y-1.5">
                {booking.attachments.map((file) => (
                  <label key={file.id} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={selectedAttachmentIds.includes(file.id)}
                      onChange={() => toggleAttachment(file.id)}
                    />
                    {file.original_filename}
                  </label>
                ))}
              </div>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button size="sm" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Submitting…" : "Submit Delivery"}
          </Button>
        </div>
      )}
    </div>
  );
}