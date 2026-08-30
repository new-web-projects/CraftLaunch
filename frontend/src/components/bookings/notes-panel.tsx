"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { BookingNote } from "@/types/bookings";

interface NotesPanelProps {
  notes: BookingNote[];
  onAddNote: (content: string) => Promise<void>;
}

export function NotesPanel({ notes, onAddNote }: NotesPanelProps) {
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (content.trim().length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await onAddNote(content.trim());
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't add that note.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      {notes.length > 0 && (
        <div className="space-y-3">
          {notes.map((note) => (
            <div key={note.id} className="rounded-md border border-border bg-card p-3 text-sm">
              <p className="text-foreground">{note.content}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {note.author?.full_name || note.author?.username} ·{" "}
                {new Date(note.created_at).toLocaleDateString()}
                {note.is_internal && " · Internal"}
              </p>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Add a note for everyone on this project…"
          rows={2}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button size="sm" variant="outline" onClick={handleSubmit} disabled={submitting || content.trim().length === 0}>
          {submitting ? "Adding…" : "Add Note"}
        </Button>
      </div>
    </div>
  );
}