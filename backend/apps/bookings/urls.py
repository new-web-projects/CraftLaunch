from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.BookingListCreateView.as_view(), name="list-create"),
    # Static paths before <uuid:pk> ones by convention — the UUID
    # converter wouldn't actually match these words, but keeping
    # collection-level routes grouped together up top is clearer to
    # read.
    path("dashboard/customer/", views.CustomerDashboardView.as_view(), name="dashboard-customer"),
    path("dashboard/developer/", views.DeveloperDashboardView.as_view(), name="dashboard-developer"),
    path("requests/", views.DeveloperProjectRequestListView.as_view(), name="requests"),
    path("notifications/", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<int:notification_id>/read/",
        views.NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    path("<uuid:pk>/", views.BookingDetailView.as_view(), name="detail"),
    path("<uuid:pk>/cancel/", views.BookingCancelView.as_view(), name="cancel"),
    path("<uuid:pk>/timeline/", views.BookingTimelineView.as_view(), name="timeline"),
    path("<uuid:pk>/attachments/", views.AttachmentUploadView.as_view(), name="attachment-upload"),
    path(
        "<uuid:pk>/attachments/<uuid:attachment_id>/",
        views.AttachmentDeleteView.as_view(),
        name="attachment-delete",
    ),
    # Part 5 — project request accept/reject
    path("<uuid:pk>/accept/", views.ProjectAcceptView.as_view(), name="accept"),
    path("<uuid:pk>/reject/", views.ProjectRejectView.as_view(), name="reject"),
    # Part 5 — assigned-developer project management
    path("<uuid:pk>/start/", views.ProjectStartView.as_view(), name="start"),
    path(
        "<uuid:pk>/mark-waiting-for-customer/",
        views.ProjectMarkWaitingForCustomerView.as_view(),
        name="mark-waiting-for-customer",
    ),
    path("<uuid:pk>/mark-ready/", views.ProjectMarkReadyView.as_view(), name="mark-ready"),
    # Part 5 — milestones
    path("<uuid:pk>/milestones/", views.MilestoneListView.as_view(), name="milestones"),
    path(
        "<uuid:pk>/milestones/<int:milestone_id>/",
        views.MilestoneUpdateView.as_view(),
        name="milestone-update",
    ),
    # Part 5 — delivery
    path("<uuid:pk>/delivery/", views.DeliveryView.as_view(), name="delivery"),
    path("<uuid:pk>/delivery/accept/", views.DeliveryAcceptView.as_view(), name="delivery-accept"),
    # Part 5 — revisions
    path("<uuid:pk>/revisions/", views.RevisionRequestListCreateView.as_view(), name="revisions"),
    # Part 5 — notes and requirements
    path("<uuid:pk>/notes/", views.BookingNoteListCreateView.as_view(), name="notes"),
    path("<uuid:pk>/requirements/", views.BookingRequirementListCreateView.as_view(), name="requirements"),
]