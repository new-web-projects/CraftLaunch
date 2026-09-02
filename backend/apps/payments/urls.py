from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    # Advance payment
    path(
        "bookings/<uuid:pk>/advance/order/",
        views.AdvancePaymentOrderCreateView.as_view(),
        name="advance-order-create",
    ),
    path(
        "bookings/<uuid:pk>/advance/verify/",
        views.AdvancePaymentVerifyView.as_view(),
        name="advance-verify",
    ),
    path(
        "bookings/<uuid:pk>/advance/status/",
        views.AdvancePaymentStatusView.as_view(),
        name="advance-status",
    ),
    # Final payment
    path(
        "bookings/<uuid:pk>/final/order/",
        views.FinalPaymentOrderCreateView.as_view(),
        name="final-order-create",
    ),
    path(
        "bookings/<uuid:pk>/final/verify/",
        views.FinalPaymentVerifyView.as_view(),
        name="final-verify",
    ),
    path(
        "bookings/<uuid:pk>/final/status/",
        views.FinalPaymentStatusView.as_view(),
        name="final-status",
    ),
    # Cross-phase
    path("bookings/<uuid:pk>/summary/", views.ProjectPaymentSummaryView.as_view(), name="summary"),
    path("history/", views.PaymentHistoryView.as_view(), name="history"),
    # Admin
    path("admin/payments/", views.AdminPaymentListView.as_view(), name="admin-payment-list"),
    # Razorpay calls this directly — no auth, signature-verified internally.
    path("webhook/", views.RazorpayWebhookView.as_view(), name="webhook"),
]