from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.tokens import default_token_generator as password_reset_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

__all__ = [
    "password_reset_token",
    "email_verification_token",
    "encode_uid",
    "decode_uid",
]


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Same mechanism Django uses for password-reset tokens (signed hash
    of pk + timestamp + a piece of state that changes once the token is
    used, so it can't be replayed), reused here with
    `is_email_verified` as that piece of state instead of the password
    hash.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.is_email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()


def encode_uid(pk) -> str:
    return urlsafe_base64_encode(force_bytes(pk))


def decode_uid(uidb64: str) -> str:
    return force_str(urlsafe_base64_decode(uidb64))