import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from gary_api import db, logs, mail
from gary_api.models import (
    EmailVerificationToken,
    PasswordResetToken,
    Session,
    User,
)
from gary_api.passwords import (
    MINIMUM_LENGTH,
    hash_password,
    new_token,
    token_digest,
    verify_password,
)

SESSION_LIFETIME = timedelta(days=30)
RESET_LIFETIME = timedelta(hours=1)
# Longer than a reset: this one is read at leisure, often on another device.
VERIFICATION_LIFETIME = timedelta(hours=24)

# Deliberately the same for a wrong password and an address with no account:
# telling them apart turns sign-in into a way to ask who has an account.
INVALID_CREDENTIALS = "Invalid email or password"

logger = logs.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

Db = Annotated[AsyncSession, Depends(db.session)]


def web_base_url() -> str:
    return os.environ.get("WEB_BASE_URL", "http://localhost:3000")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalise_email(email: str) -> str:
    return email.strip().lower()


class Password(BaseModel):
    password: str = Field(min_length=MINIMUM_LENGTH)


class DisplayName(BaseModel):
    display_name: str = Field(max_length=100)

    @field_validator("display_name")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("display_name cannot be blank")
        return cleaned


class RegisterRequest(Password, DisplayName):
    email: EmailStr


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MINIMUM_LENGTH)


class ResetRequest(BaseModel):
    email: EmailStr


class ResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=MINIMUM_LENGTH)


class VerifyEmailRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    email_verified: bool


class SignedInResponse(UserResponse):
    token: str
    expires_at: datetime


def _as_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "email_verified": user.email_verified_at is not None,
    }


async def _issue_session(database: AsyncSession, user: User) -> tuple[str, datetime]:
    token = new_token()
    expires_at = _now() + SESSION_LIFETIME
    database.add(
        Session(user_id=user.id, token_hash=token_digest(token), expires_at=expires_at)
    )
    await database.commit()
    return token, expires_at


async def _bearer_session(database: AsyncSession, authorization: str | None) -> Session:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    token = authorization.split(" ", 1)[1].strip()
    found = await database.scalar(
        select(Session).where(Session.token_hash == token_digest(token))
    )
    if found is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    if found.expires_at <= _now():
        # Clear it out rather than leave it to be re-checked on every request.
        await database.delete(found)
        await database.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    return found


async def current_session(
    database: Db, authorization: Annotated[str | None, Header()] = None
) -> Session:
    return await _bearer_session(database, authorization)


async def current_user(
    database: Db, session: Annotated[Session, Depends(current_session)]
) -> User:
    return await database.get(User, session.user_id)


CurrentSession = Annotated[Session, Depends(current_session)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, database: Db) -> SignedInResponse:
    email = normalise_email(request.email)

    if await database.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "That email address is already registered"
        )

    user = User(
        email=email,
        display_name=request.display_name,
        password_hash=hash_password(request.password),
    )
    database.add(user)
    await database.commit()

    await _issue_verification(database, user)

    token, expires_at = await _issue_session(database, user)
    return SignedInResponse(**_as_user(user), token=token, expires_at=expires_at)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def sign_in(request: SignInRequest, database: Db) -> SignedInResponse:
    user = await database.scalar(
        select(User).where(User.email == normalise_email(request.email))
    )
    if user is None or not verify_password(user.password_hash, request.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    token, expires_at = await _issue_session(database, user)
    return SignedInResponse(**_as_user(user), token=token, expires_at=expires_at)


@router.delete("/sessions/current", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(
    database: Db, authorization: Annotated[str | None, Header()] = None
) -> None:
    # Idempotent: signing out of nothing is the state the caller wanted.
    try:
        session = await _bearer_session(database, authorization)
    except HTTPException:
        return

    await database.delete(session)
    await database.commit()


@router.get("/me")
async def read_me(user: CurrentUser) -> UserResponse:
    return UserResponse(**_as_user(user))


@router.patch("/me")
async def update_me(
    request: DisplayName, user: CurrentUser, database: Db
) -> UserResponse:
    user.display_name = request.display_name
    database.add(user)
    await database.commit()
    return UserResponse(**_as_user(user))


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    user: CurrentUser,
    session: CurrentSession,
    database: Db,
) -> None:
    if not verify_password(user.password_hash, request.current_password):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "That is not your current password"
        )

    user.password_hash = hash_password(request.new_password)
    database.add(user)
    # You change a password because you think someone else has it, so every
    # other session it could have been used on has to go. This one stays,
    # because signing the user out of the page they just used is a puzzle.
    await database.execute(
        delete(Session).where(Session.user_id == user.id, Session.id != session.id)
    )
    await database.commit()


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(request: ResetRequest, database: Db) -> None:
    user = await database.scalar(
        select(User).where(User.email == normalise_email(request.email))
    )
    if user is None:
        # Same status, same body, no mail. Anything else lists who has an
        # account here.
        return

    # A new link supersedes the old one; two live links doubles the window
    # in which a leaked email is worth something.
    await database.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )

    token = new_token()
    database.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_digest(token),
            expires_at=_now() + RESET_LIFETIME,
        )
    )
    await database.commit()

    # A provider outage must not change the answer. Raising here would 500 for
    # an address that exists while an unknown one still got 202, which is the
    # enumeration this endpoint is shaped to avoid. Nobody can reset while mail
    # is down either way; the log is where that gets noticed.
    try:
        await _send_reset_link(user, token)
    except mail.MailError:
        logger.exception("mail.failed", kind="password_reset", to=user.email)


async def _send_reset_link(user: User, token: str) -> None:
    await mail.send(
        mail.Message(
            to=user.email,
            subject="Reset your gary password",
            text=(
                f"Hello {user.display_name},\n\n"
                "Someone asked to reset your gary password. Follow this link "
                "within the hour to set a new one:\n\n"
                f"{web_base_url()}/reset?token={token}\n\n"
                "If that was not you, nothing has changed and you can ignore "
                "this message.\n"
            ),
        )
    )


# One message for never-issued, already-used and expired: which of the three
# it was is not the holder's business.
DEAD_LINK = "That reset link has expired or has already been used"


async def _usable_reset(database: AsyncSession, token: str) -> PasswordResetToken:
    reset = await database.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_digest(token)
        )
    )
    if reset is None or reset.used_at is not None or reset.expires_at <= _now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, DEAD_LINK)

    return reset


@router.get("/password-reset/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def check_password_reset(token: str, database: Db) -> None:
    """Whether a link is still good, so gary-web can say so on open.

    Read-only and deliberately does not consume the token: opening the page
    must not be what burns the one use.
    """
    await _usable_reset(database, token)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(request: ResetConfirmRequest, database: Db) -> None:
    reset = await _usable_reset(database, request.token)

    user = await database.get(User, reset.user_id)
    user.password_hash = hash_password(request.new_password)
    reset.used_at = _now()
    database.add_all([user, reset])

    # Reset is the recovery path for an account someone else may hold, so
    # every session goes, including any they opened.
    await database.execute(delete(Session).where(Session.user_id == user.id))
    await database.commit()

    # The audience for this one is the person who did *not* do it.
    await _notify(
        user,
        "Your gary password was changed",
        f"Hello {user.display_name},\n\n"
        "Your gary password has just been changed, and everything signed in "
        "with the old one has been signed out.\n\n"
        "If this was not you, reset it again now — whoever did it can read "
        "this address.\n",
    )

DEAD_VERIFICATION = "That verification link has expired or has already been used"


async def _notify(user: User, subject: str, body: str) -> None:
    """A courtesy email that carries no link and asks for nothing.

    Never raises: these confirm something that has already happened, and
    failing the request after the fact would be a lie about what happened.
    """
    try:
        await mail.send(mail.Message(to=user.email, subject=subject, text=body))
    except mail.MailError:
        logger.exception("mail.failed", kind="notification", subject=subject, to=user.email)


async def _issue_verification(database: AsyncSession, user: User) -> None:
    """Mint a link and mail it. Never raises — see the comment below."""
    # A new link supersedes any older one, so a forwarded email cannot be
    # used after the owner asked for a fresh link.
    await database.execute(
        delete(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
    )

    token = new_token()
    database.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=token_digest(token),
            expires_at=_now() + VERIFICATION_LIFETIME,
        )
    )
    await database.commit()

    # Registration must not hinge on the mail provider. Losing the account
    # because the email could not go out is worse than an unverified account
    # and a resend button, so this is logged and swallowed.
    try:
        await mail.send(
            mail.Message(
                to=user.email,
                subject="Confirm your gary address",
                text=(
                    f"Hello {user.display_name},\n\n"
                    "Confirm this address so gary knows it can reach you. "
                    "The link is good for a day:\n\n"
                    f"{web_base_url()}/verify?token={token}\n\n"
                    "If you did not sign up for gary, you can ignore this.\n"
                ),
            )
        )
    except mail.MailError:
        logger.exception("mail.failed", kind="email_verification", to=user.email)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(request: VerifyEmailRequest, database: Db) -> None:
    """Confirm an address from the emailed link.

    Deliberately needs no session: the email is often opened on a device
    that has never signed in, and making people sign in first would be a
    worse experience for no security gain — the token is the credential.
    """
    verification = await database.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_digest(request.token)
        )
    )
    if (
        verification is None
        or verification.used_at is not None
        or verification.expires_at <= _now()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, DEAD_VERIFICATION)

    user = await database.get(User, verification.user_id)
    user.email_verified_at = _now()
    verification.used_at = _now()
    database.add_all([user, verification])
    await database.commit()

    await _notify(
        user,
        "Your gary address is confirmed",
        f"Hello {user.display_name},\n\n"
        "Your email address is now confirmed and your gary account is all "
        "set.\n\n"
        "If you did not sign up for gary, someone has used your address — "
        "nothing else has been done with it, and you can ignore this.\n",
    )


@router.post("/verify-email/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(user: CurrentUser, database: Db) -> None:
    if user.email_verified_at is not None:
        # Already done. Same status either way, and no mail to send.
        return

    await _issue_verification(database, user)
