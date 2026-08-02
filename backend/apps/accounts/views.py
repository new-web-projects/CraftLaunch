from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from django.utils.encoding import DjangoUnicodeDecodeError
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import OutstandingToken, RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from .cookies import clear_refresh_cookie, set_refresh_cookie
from .emails import send_password_reset_email, send_verification_email
from .jwt import issue_tokens_for_user
from .models import Role, UserSession
from .permissions import IsSuperAdmin
from .serializers import (
    AdminRegisterSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    SessionSerializer,
    UpdateProfileSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .throttling import LoginRateThrottle
from .tokens import decode_uid, email_verification_token, password_reset_token

User = get_user_model()

GENERIC_RESET_MESSAGE = "If an account with that email exists, a reset link has been sent."
GENERIC_VERIFY_MESSAGE = "If an account with that email exists and isn't verified yet, a new link has been sent."


class RegisterView(GenericAPIView):
    """POST /api/auth/register/ — Customer or Developer only."""

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user)
        return Response(
            {"detail": "Registration successful. Check your email to verify your account."},
            status=status.HTTP_201_CREATED,
        )


class AdminRegisterView(GenericAPIView):
    """
    POST /api/auth/register/admin/ — creates a regular Admin account.
    Only a Super Admin may call this (see permissions.IsSuperAdmin);
    there is deliberately no public path to the Admin role.
    """

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = AdminRegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user)
        return Response(
            {"detail": f"Admin account created for {user.username}. They must verify their email before logging in."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(GenericAPIView):
    """
    POST /api/auth/login/ — accepts either email or username as
    `identifier`. Issues an access token in the response body and sets
    the refresh token as an httpOnly cookie (never in the JSON body,
    so it's unreachable from JS even if the frontend has an XSS bug).
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]
        remember_me = serializer.validated_data.get("remember_me", False)

        try:
            candidate = User.objects.get(Q(username__iexact=identifier) | Q(email__iexact=identifier))
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            candidate = None

        if candidate and candidate.is_locked():
            return Response(
                {"detail": "Account temporarily locked due to repeated failed attempts. Try again later.", "code": "account_locked"},
                status=status.HTTP_423_LOCKED,
            )

        user = authenticate(request, username=identifier, password=password)

        if user is None:
            if candidate and not candidate.check_password(password):
                candidate.register_failed_login()
                return Response(
                    {"detail": "Invalid credentials.", "code": "invalid_credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if candidate and not candidate.is_active:
                return Response(
                    {"detail": "Please verify your email before logging in.", "code": "email_not_verified"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"detail": "Invalid credentials.", "code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.register_successful_login()
        refresh = issue_tokens_for_user(user, request, remember_me=remember_me)

        response = Response(
            {
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, str(refresh), remember_me=remember_me)
        return response


class RefreshView(APIView):
    """
    POST /api/auth/refresh/ — reads the refresh token from the httpOnly
    cookie (not the request body, unlike SimpleJWT's default view).
    With ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION both on, the
    old refresh token is blacklisted and a new one issued every call.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        old_token_str = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not old_token_str:
            return Response({"detail": "No refresh token provided.", "code": "no_refresh_token"}, status=401)

        try:
            old_token = RefreshToken(old_token_str)
        except TokenError:
            response = Response({"detail": "Session expired. Please log in again.", "code": "session_expired"}, status=401)
            clear_refresh_cookie(response)
            return response

        old_jti = str(old_token["jti"])
        remember_me = old_token.get("remember_me", False)

        try:
            # Blacklist FIRST, while old_token's jti/exp/iat still reflect
            # the token as originally issued — new_refresh is the same
            # object, so mutating its claims below would otherwise cause
            # blacklist() to record the *new* jti instead of the old one,
            # leaving the original refresh token silently still usable.
            if getattr(settings, "SIMPLE_JWT", {}).get("BLACKLIST_AFTER_ROTATION", True):
                try:
                    old_token.blacklist()
                except AttributeError:
                    pass
            new_refresh = old_token
            new_refresh.set_jti()
            new_refresh.set_exp()
            new_refresh.set_iat()
        except TokenError as e:
            raise InvalidToken(e.args[0])

        new_access = new_refresh.access_token

        UserSession.objects.filter(jti=old_jti).update(jti=str(new_refresh["jti"]))

        response = Response({"access": str(new_access)}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, str(new_refresh), remember_me=bool(remember_me))
        return response


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklists the current session's
    refresh token and clears both cookies."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_str = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if token_str:
            try:
                token = RefreshToken(token_str)
                token.blacklist()
                UserSession.objects.filter(jti=str(token["jti"])).delete()
            except TokenError:
                pass

        response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


class LogoutAllView(APIView):
    """POST /api/auth/logout-all/ — blacklists every outstanding
    refresh token for the current user (all devices), including the
    one making this request."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        outstanding = OutstandingToken.objects.filter(user=request.user)
        blacklisted_jtis = set(
            BlacklistedToken.objects.filter(token__user=request.user).values_list("token__jti", flat=True)
        )
        for token in outstanding:
            if token.jti not in blacklisted_jtis:
                BlacklistedToken.objects.get_or_create(token=token)

        UserSession.objects.filter(user=request.user).delete()

        response = Response({"detail": "Logged out of all devices."}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


class VerifyEmailView(GenericAPIView):
    """POST /api/auth/verify-email/ — activates the account (this *is*
    the "Account Activation" step, tied directly to verification)."""

    permission_classes = [AllowAny]
    serializer_class = VerifyEmailSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pk = decode_uid(serializer.validated_data["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, DjangoUnicodeDecodeError):
            return Response({"detail": "Invalid verification link.", "code": "invalid_link"}, status=400)

        if user.is_email_verified:
            return Response({"detail": "Email already verified. You can log in."}, status=200)

        if not email_verification_token.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "This link is invalid or has expired.", "code": "invalid_or_expired"}, status=400)

        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])
        return Response({"detail": "Email verified. You can now log in."}, status=200)


class ResendVerificationView(GenericAPIView):
    """POST /api/auth/resend-verification/ — always returns the same
    generic message so it can't be used to enumerate registered emails."""

    permission_classes = [AllowAny]
    serializer_class = ResendVerificationSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email__iexact=serializer.validated_data["email"])
            if not user.is_email_verified:
                send_verification_email(user)
        except User.DoesNotExist:
            pass
        return Response({"detail": GENERIC_VERIFY_MESSAGE}, status=200)


class ForgotPasswordView(GenericAPIView):
    """POST /api/auth/forgot-password/ — same anti-enumeration
    approach as ResendVerificationView."""

    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email__iexact=serializer.validated_data["email"])
            send_password_reset_email(user)
        except User.DoesNotExist:
            pass
        return Response({"detail": GENERIC_RESET_MESSAGE}, status=200)


class ResetPasswordView(GenericAPIView):
    """POST /api/auth/reset-password/"""

    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pk = decode_uid(serializer.validated_data["uid"])
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError, DjangoUnicodeDecodeError):
            return Response({"detail": "Invalid reset link.", "code": "invalid_link"}, status=400)

        if not password_reset_token.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "This link is invalid or has expired.", "code": "invalid_or_expired"}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["password", "failed_login_attempts", "locked_until"])
        return Response({"detail": "Password reset. You can now log in with your new password."}, status=200)


class MeView(GenericAPIView):
    """GET/PATCH /api/auth/me/ — current authenticated user + profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.update(request.user, serializer.validated_data)
        return Response(UserSerializer(user).data)


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed. Please log in again on other devices."}, status=200)


class DeleteAccountRequestView(APIView):
    """
    POST /api/auth/delete-account/ — records a request rather than
    deleting anything immediately. Actual deletion/processing (and any
    grace period, admin review, or data export) is a future part; this
    part only needs the request to be captured reliably.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.utils import timezone

        request.user.deletion_requested_at = timezone.now()
        request.user.save(update_fields=["deletion_requested_at"])
        return Response({"detail": "Account deletion requested. Our team will follow up before anything is removed."}, status=200)


class SessionListView(GenericAPIView):
    """GET /api/auth/sessions/ — the signed-in user's active devices."""

    permission_classes = [IsAuthenticated]
    serializer_class = SessionSerializer

    def get(self, request):
        current_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        current_jti = None
        if current_token:
            try:
                current_jti = str(RefreshToken(current_token)["jti"])
            except TokenError:
                pass

        sessions = UserSession.objects.filter(user=request.user)
        serializer = self.get_serializer(sessions, many=True, context={"current_jti": current_jti})
        return Response(serializer.data)


class SessionRevokeView(APIView):
    """DELETE /api/auth/sessions/<id>/ — revoke one specific session."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id):
        try:
            session = UserSession.objects.get(id=session_id, user=request.user)
        except UserSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=404)

        for outstanding in OutstandingToken.objects.filter(jti=session.jti):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        session.delete()
        return Response({"detail": "Session revoked."}, status=200)