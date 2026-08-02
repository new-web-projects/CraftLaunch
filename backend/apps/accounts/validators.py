import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """
    Requires at least one uppercase letter, one lowercase letter, one
    digit and one special character. Runs alongside Django's built-in
    validators (minimum length, similarity to user attributes, common
    password list, not-entirely-numeric) configured in
    AUTH_PASSWORD_VALIDATORS in settings/base.py — this one adds
    character-class complexity, which none of the built-ins check.
    """

    UPPERCASE_RE = re.compile(r"[A-Z]")
    LOWERCASE_RE = re.compile(r"[a-z]")
    DIGIT_RE = re.compile(r"\d")
    SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")

    def validate(self, password, user=None):
        if not self.UPPERCASE_RE.search(password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )
        if not self.LOWERCASE_RE.search(password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lower",
            )
        if not self.DIGIT_RE.search(password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_no_digit",
            )
        if not self.SPECIAL_RE.search(password):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Your password must contain an uppercase letter, a lowercase "
            "letter, a digit, and a special character."
        )