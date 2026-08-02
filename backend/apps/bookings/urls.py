from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.BookingListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", views.BookingDetailView.as_view(), name="detail"),
    path("<uuid:pk>/cancel/", views.BookingCancelView.as_view(), name="cancel"),
    path("<uuid:pk>/timeline/", views.BookingTimelineView.as_view(), name="timeline"),
    path("<uuid:pk>/attachments/", views.AttachmentUploadView.as_view(), name="attachment-upload"),
    path(
        "<uuid:pk>/attachments/<uuid:attachment_id>/",
        views.AttachmentDeleteView.as_view(),
        name="attachment-delete",
    ),
]