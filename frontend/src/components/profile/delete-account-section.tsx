"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiClient } from "@/lib/api-client";

export function DeleteAccountSection() {
  const [confirming, setConfirming] = useState(false);
  const [status, setStatus] = useState<"idle" | "requested" | "error">("idle");

  async function handleConfirm() {
    try {
      await apiClient.post("/api/auth/delete-account/");
      setStatus("requested");
    } catch {
      setStatus("error");
    } finally {
      setConfirming(false);
    }
  }

  if (status === "requested") {
    return (
      <Alert variant="success">
        <AlertDescription>
          Deletion requested. Our team will follow up before anything is removed.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-3">
      {status === "error" && (
        <Alert variant="destructive">
          <AlertDescription>Couldn&apos;t submit the request. Please try again.</AlertDescription>
        </Alert>
      )}
      <p className="text-sm text-muted-foreground">
        This submits a request for your account to be deleted — it doesn&apos;t happen
        immediately.
      </p>
      {confirming ? (
        <div className="flex gap-2">
          <Button variant="destructive" size="sm" onClick={handleConfirm}>
            Yes, request deletion
          </Button>
          <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <Button variant="destructive" size="sm" onClick={() => setConfirming(true)}>
          Request account deletion
        </Button>
      )}
    </div>
  );
}