import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

MINIMUM_LENGTH = 8
TOKEN_BYTES = 32

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, VerifyMismatchError):
        return False


def new_token() -> str:
    """An opaque session or reset token.

    secrets, not uuid4: these are bearer credentials and want a generator
    documented for that, rather than one whose job is uniqueness.
    """
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_digest(token: str) -> str:
    """What gets stored for a token.

    Plain SHA-256 rather than argon2: a 256-bit random token has nothing to
    brute force, and this is looked up on every authenticated request.
    """
    return hashlib.sha256(token.encode()).hexdigest()
