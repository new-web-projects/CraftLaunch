"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiClient } from "@/lib/api-client";
import { ApiError } from "@/types/auth";

type Status = "verifying" | "success" | "error" | "resend-only";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const uid = searchParams.get("uid");
  const token = searchParams.get("token");
  const resendEmail = searchParams.get("resend");

  const [status, setStatus] = useState<Status>(uid && token ? "verifying" : "resend-only");
  const [message, setMessage] = useState<string>("");
  const [resendSent, setResendSent] = useState(false);

  useEffect(() => {
    if (!uid || !token) return;
    apiClient
      .post<{ detail: string }>("/api/auth/verify-email/", { uid, token }, { skipAuthRetry: true })
      .then((data) => {
        setStatus("success");
        setMessage(data.detail);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof ApiError ? err.body.detail ?? "" : "This link is invalid or has expired.");
      });
  }, [uid, token]);

  async function handleResend() {
    if (!resendEmail) return;
    try {
      await apiClient.post("/api/auth/resend-verification/", { email: resendEmail }, { skipAuthRetry: true });
    } finally {
      setResendSent(true);
    }
  }

  if (status === "verifying") {
    return <p className="text-sm text-muted-foreground">Verifying your email…</p>;
  }

  if (status === "success") {
    return (
      <div className="space-y-4">
        <Alert variant="success">
          <AlertDescription>{message}</AlertDescription>
        </Alert>
        <Button asChild className="w-full">
          <Link href="/login">Log in</Link>
        </Button>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <AlertDescription>{message}</AlertDescription>
        </Alert>
        <p className="text-sm text-muted-foreground">
          Need a new link?{" "}
          <Link href="/verify-email" className="underline">
            Request another
          </Link>
        </p>
      </div>
    );
  }

  // resend-only: arrived without uid/token, likely from the login
  // page's "resend verification" prompt.
  return (
    <div className="space-y-4">
      {resendSent ? (
        <Alert variant="success">
          <AlertDescription>
            If that account exists and isn&apos;t verified yet, a new link is on its way.
          </AlertDescription>
        </Alert>
      ) : resendEmail ? (
        <Button onClick={handleResend} className="w-full">
          Resend verification email to {resendEmail}
        </Button>
      ) : (
        <p className="text-sm text-muted-foreground">
          Use the link from your verification email, or go back to{" "}
          <Link href="/register" className="underline">
            sign up
          </Link>{" "}
          again if you no longer have it.
        </p>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Email verification</CardTitle>
          <CardDescription>Confirming your account.</CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
            <VerifyEmailContent />
          </Suspense>
        </CardContent>
      </Card>
    </main>
  );
}