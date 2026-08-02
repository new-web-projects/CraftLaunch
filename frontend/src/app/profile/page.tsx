"use client";

import { RequireAuth } from "@/components/auth/require-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ProfileDetailsForm } from "@/components/profile/profile-details-form";
import { ChangePasswordForm } from "@/components/profile/change-password-form";
import { ActiveSessions } from "@/components/profile/active-sessions";
import { DeleteAccountSection } from "@/components/profile/delete-account-section";
import { useAuth } from "@/contexts/auth-context";

function ProfileContent() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <main className="mx-auto w-full max-w-2xl space-y-6 px-6 py-12">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">My Profile</h1>
        <p className="text-sm text-muted-foreground">
          Signed in as {user.email}
          {user.is_email_verified ? (
            <span className="ml-2 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-400">
              Verified
            </span>
          ) : (
            <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
              Unverified
            </span>
          )}
          <span className="ml-2 rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
            {user.role}
          </span>
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile details</CardTitle>
          <CardDescription>Your name and contact information.</CardDescription>
        </CardHeader>
        <CardContent>
          <ProfileDetailsForm user={user} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Password</CardTitle>
          <CardDescription>Change your password.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active sessions</CardTitle>
          <CardDescription>Devices currently signed in to your account.</CardDescription>
        </CardHeader>
        <CardContent>
          <ActiveSessions />
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Danger zone</CardTitle>
          <CardDescription>Request your account be deleted.</CardDescription>
        </CardHeader>
        <CardContent>
          <DeleteAccountSection />
        </CardContent>
      </Card>
    </main>
  );
}

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfileContent />
    </RequireAuth>
  );
}