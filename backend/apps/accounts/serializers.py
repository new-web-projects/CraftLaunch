from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import AdminProfile, CustomerProfile, DeveloperProfile, Role, UserSession

User = get_user_model()

PROFILE_MODELS = {
    Role.CUSTOMER: CustomerProfile,
    Role.DEVELOPER: DeveloperProfile,
    Role.ADMIN: AdminProfile,
}


class ProfileSerializer(serializers.ModelSerializer):
    """
    Shared shape for all three profile tables (CustomerProfile,
    DeveloperProfile, AdminProfile) — they're identical today by
    design (see models.BaseProfile), so one serializer works for all
    three; the view picks which *model* based on request.user.role.
    """

    class Meta:
        fields = ["profile_picture_url", "phone", "country", "timezone", "language"]
        extra_kwargs = {field: {"required": False} for field in fields}


class CustomerProfileSerializer(ProfileSerializer):
    class Meta(ProfileSerializer.Meta):
        model = CustomerProfile


class DeveloperProfileSerializer(ProfileSerializer):
    class Meta(ProfileSerializer.Meta):
        model = DeveloperProfile


class AdminProfileSerializer(ProfileSerializer):
    class Meta(ProfileSerializer.Meta):
        model = AdminProfile


PROFILE_SERIALIZERS = {
    Role.CUSTOMER: CustomerProfileSerializer,
    Role.DEVELOPER: DeveloperProfileSerializer,
    Role.ADMIN: AdminProfileSerializer,
}


def profile_serializer_for(role: str):
    return PROFILE_SERIALIZERS[role]


class UserSerializer(serializers.ModelSerializer):
    """Read-mostly representation used by GET /api/auth/me/."""

    full_name = serializers.CharField(read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_email_verified",
            "date_joined",
            "profile",
        ]
        read_only_fields = ["id", "email", "role", "is_email_verified", "date_joined"]

    def get_profile(self, user):
        profile_model = PROFILE_MODELS[user.role]
        profile, _created = profile_model.objects.get_or_create(user=user)
        return profile_serializer_for(user.role)(profile).data


class UpdateProfileSerializer(serializers.Serializer):
    """
    PATCH /api/auth/me/ — a thin composite over User's editable fields
    plus the role-appropriate profile's fields, so the frontend can
    send one flat payload instead of knowing about two tables.
    """

    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    profile_picture_url = serializers.URLField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    country = serializers.CharField(required=False, allow_blank=True, max_length=2)
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    language = serializers.CharField(required=False, allow_blank=True, max_length=8)

    def update(self, user, validated_data):
        user_fields = {"first_name", "last_name"}
        for field in user_fields & validated_data.keys():
            setattr(user, field, validated_data[field])
        user.save(update_fields=list(user_fields & validated_data.keys()) or None)

        profile_model = PROFILE_MODELS[user.role]
        profile, _created = profile_model.objects.get_or_create(user=user)
        profile_fields = validated_data.keys() - user_fields
        for field in profile_fields:
            setattr(profile, field, validated_data[field])
        if profile_fields:
            profile.save(update_fields=list(profile_fields))
        return user


class BaseRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm", "first_name", "last_name"]

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def _create_with_role(self, validated_data, role: str):
        password = validated_data.pop("password")
        user = User(role=role, is_active=False, **validated_data)
        user.set_password(password)
        user.save()
        PROFILE_MODELS[role].objects.create(user=user)
        return user


class RegisterSerializer(BaseRegisterSerializer):
    """Public registration — Customer or Developer only. Admin
    accounts can never be created through this serializer; see
    AdminRegisterSerializer."""

    role = serializers.ChoiceField(choices=[Role.CUSTOMER, Role.DEVELOPER])

    class Meta(BaseRegisterSerializer.Meta):
        fields = BaseRegisterSerializer.Meta.fields + ["role"]

    def create(self, validated_data):
        role = validated_data.pop("role")
        return self._create_with_role(validated_data, role)


class AdminRegisterSerializer(BaseRegisterSerializer):
    """
    Creates a regular Admin (role=ADMIN, is_staff=True,
    is_superuser=False). Never exposed publicly — the view enforces
    IsSuperAdmin. The very first Super Admin can't come from this
    serializer at all (nobody would exist yet to authorize it); that
    one is created with `python manage.py createsuperuser`.
    """

    def create(self, validated_data):
        user = self._create_with_role(validated_data, Role.ADMIN)
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, user=self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email or username")
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False, required=False)


class SessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = ["id", "user_agent", "ip_address", "created_at", "last_seen_at", "is_current"]

    def get_is_current(self, obj) -> bool:
        return obj.jti == self.context.get("current_jti")