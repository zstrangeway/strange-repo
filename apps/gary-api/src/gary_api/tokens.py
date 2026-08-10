import hashlib
import secrets

TOKEN_BYTES = 32


def new_token() -> str:
    """An opaque session token.

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
