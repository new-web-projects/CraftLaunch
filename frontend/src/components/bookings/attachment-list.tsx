"use client";

import { useRef, useState } from "react";
import { FileText, Trash2, Upload } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { bookingsApi } from "@/lib/bookings-api";
import { ApiError } from "@/types/auth";
import type { ProjectAttachment } from "@/types/bookings";

const ALLOWED_EXTENSIONS = "jpg,jpeg,png,gif,webp,svg,pdf,zip,doc,docx,xls,xlsx,csv,txt"
  .split(",")
  .map((e) => `.${e}`)
  .join(",");

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface AttachmentListProps {
  bookingId: string;
  attachments: ProjectAttachment[];
  canModify: boolean;
}

export function AttachmentList({ bookingId, attachments: initial, canModify }: AttachmentListProps) {
  const [attachments, setAttachments] = useState(initial);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFileSelected(file: File | undefined) {
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const attachment = await bookingsApi.uploadAttachment(bookingId, file);
      setAttachments((prev) => [attachment, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.body.detail ?? "Upload failed. Please try again." : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleDelete(attachmentId: string) {
    setError(null);
    const previous = attachments;
    setAttachments((prev) => prev.filter((a) => a.id !== attachmentId));
    try {
      await bookingsApi.deleteAttachment(bookingId, attachmentId);
    } catch (err) {
      setAttachments(previous);
      setError(err instanceof ApiError ? err.body.detail ?? "Couldn't delete that file." : "Couldn't delete that file.");
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {attachments.length === 0 ? (
        <p className="text-sm text-muted-foreground">No files uploaded yet.</p>
      ) : (
        <ul className="space-y-2">
          {attachments.map((attachment) => (
            <li
              key={attachment.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="truncate text-sm text-foreground">{attachment.original_filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatSize(attachment.file_size)} · {attachment.uploaded_by.username}
                  </p>
                </div>
              </div>
              {canModify && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Delete ${attachment.original_filename}`}
                  onClick={() => handleDelete(attachment.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canModify && (
        <div>
          <input
            ref={inputRef}
            type="file"
            accept={ALLOWED_EXTENSIONS}
            className="hidden"
            onChange={(e) => handleFileSelected(e.target.files?.[0])}
            aria-label="Upload a file"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            <Upload className="h-4 w-4" />
            {uploading ? "Uploading…" : "Upload file"}
          </Button>
          <p className="mt-1 text-xs text-muted-foreground">
            Images, PDF, ZIP, DOCX, spreadsheets, or text files. Max 25MB.
          </p>
        </div>
      )}
    </div>
  );
}