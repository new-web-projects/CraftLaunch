from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Same rules as Django's ModelBackend (password check, is_active
    check) but looks the user up by username OR email, so a single
    login form can accept either — the spec's "Email Login" and
    "Username Login" are the same endpoint, not two different ones.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(User.USERNAME_FIELD)
        if identifier is None or password is None:
            return None

        try:
            user = User.objects.get(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        except User.DoesNotExist:
            # Still run the hasher against a dummy password so a
            # nonexistent-user response takes the same time as a
            # wrong-password one (timing-attack / enumeration hardening).
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None