from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("register/admin/", views.AdminRegisterView.as_view(), name="register-admin"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-all/", views.LogoutAllView.as_view(), name="logout-all"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", views.ResendVerificationView.as_view(), name="resend-verification"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("delete-account/", views.DeleteAccountRequestView.as_view(), name="delete-account"),
    path("sessions/", views.SessionListView.as_view(), name="sessions"),
    path("sessions/<int:session_id>/", views.SessionRevokeView.as_view(), name="session-revoke"),
]