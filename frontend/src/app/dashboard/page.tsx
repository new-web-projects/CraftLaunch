"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  Clock,
  Inbox,
  PackageCheck,
  Rocket,
  Send,
  XCircle,
} from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { bookingsApi } from "@/lib/bookings-api";
import { ApiError } from "@/types/auth";
import type { CustomerDashboardData, DeveloperDashboardData } from "@/types/bookings";
import { StatCard } from "@/components/dashboard/stat-card";
import { BookingSummaryRow } from "@/components/dashboard/booking-summary-row";
import { RecentActivityFeed } from "@/components/dashboard/recent-activity-feed";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function CustomerDashboard() {
  const [data, setData] = useState<CustomerDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setData(null);
    bookingsApi
      .customerDashboard()
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your dashboard."));
  };

  // useEffect(load, []) would call the synchronous setError/setData
  // resets directly inside the effect body, which is exactly what
  // react-hooks/set-state-in-effect warns against — so the initial
  // fetch goes straight to the request here, and only the retry
  // button (a click handler, not an effect) reuses the full load()
  // with its state-clearing reset.
  useEffect(() => {
    bookingsApi
      .customerDashboard()
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your dashboard."));
  }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return <LoadingState label="Loading your dashboard…" />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Welcome back</h1>
        <p className="text-muted-foreground">Here&apos;s where things stand across your projects.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Active Projects" value={data.counts.active_projects} icon={Rocket} href="/bookings?status=accepted,in_progress,waiting_for_customer,revision_requested,ready_for_delivery" />
        <StatCard label="Pending Bookings" value={data.counts.pending_bookings} icon={Clock} href="/bookings?status=draft,submitted,awaiting_developer" />
        <StatCard label="Completed" value={data.counts.completed_projects} icon={CheckCircle2} href="/bookings?status=completed" tone="success" />
        <StatCard label="Cancelled" value={data.counts.cancelled_projects} icon={XCircle} href="/bookings?status=cancelled,rejected" />
        <StatCard
          label="Awaiting Your Action"
          value={data.counts.awaiting_your_action}
          icon={AlertTriangle}
          href="/bookings?status=waiting_for_customer,delivered"
          tone="warning"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recently Updated Projects</CardTitle>
          </CardHeader>
          <CardContent>
            {data.recently_updated.length === 0 ? (
              <EmptyState icon={PackageCheck} title="No projects yet" description="Book a package to get started." />
            ) : (
              <div className="space-y-2">
                {data.recently_updated.map((booking) => (
                  <BookingSummaryRow key={booking.id} booking={booking} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <RecentActivityFeed events={data.recent_activity} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DeveloperDashboard() {
  const [data, setData] = useState<DeveloperDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setData(null);
    bookingsApi
      .developerDashboard()
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your dashboard."));
  };

  useEffect(() => {
    bookingsApi
      .developerDashboard()
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your dashboard."));
  }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return <LoadingState label="Loading your dashboard…" />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Welcome back</h1>
        <p className="text-muted-foreground">Here&apos;s what needs your attention.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatCard label="New Requests" value={data.counts.new_project_requests} icon={Inbox} href="/dashboard/requests" tone="warning" />
        <StatCard label="Accepted" value={data.counts.accepted_projects} icon={CheckCircle2} href="/bookings?status=accepted" />
        <StatCard label="Active" value={data.counts.active_projects} icon={Briefcase} href="/bookings?status=in_progress" />
        <StatCard label="Waiting on Customer" value={data.counts.waiting_for_customer} icon={Clock} href="/bookings?status=waiting_for_customer" />
        <StatCard label="Ready for Delivery" value={data.counts.ready_for_delivery} icon={Send} href="/bookings?status=ready_for_delivery" tone="success" />
        <StatCard label="Completed" value={data.counts.completed_projects} icon={PackageCheck} href="/bookings?status=completed" tone="success" />
        <StatCard label="Cancelled" value={data.counts.cancelled_projects} icon={XCircle} href="/bookings?status=cancelled,rejected" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upcoming Deadlines</CardTitle>
          </CardHeader>
          <CardContent>
            {data.upcoming_deadlines.length === 0 ? (
              <EmptyState icon={Clock} title="No upcoming deadlines" description="Deadlines on your active projects will show up here." />
            ) : (
              <div className="space-y-2">
                {data.upcoming_deadlines.map((booking) => (
                  <BookingSummaryRow key={booking.id} booking={booking} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <RecentActivityFeed events={data.recent_activity} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  return user?.role === "DEVELOPER" ? <DeveloperDashboard /> : <CustomerDashboard />;
}