import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from gary_api import db, identity, logs
from gary_api.models import Identity, Session, User
from gary_api.tokens import new_token, token_digest

SESSION_LIFETIME = timedelta(days=30)

# What a provider is called when gary has to say its name to a person.
LABELS = {"google": "Google", "facebook": "Facebook", "apple": "Apple"}

ONLY_WAY_IN = "That is your only way to sign in"

logger = logs.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

Db = Annotated[AsyncSession, Depends(db.session)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def label(provider: str) -> str:
    return LABELS.get(provider, provider)


class DisplayName(BaseModel):
    display_name: str = Field(max_length=100)

    @field_validator("display_name")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Your display name cannot be blank")
        return cleaned


class ProviderResponse(BaseModel):
    name: str
    label: str
    authorization_url: str


class SignInRequest(BaseModel):
    provider: str
    code: str
    redirect_uri: str
    # Apple puts the name in the first callback and never again, so a client
    # that was handed one passes it along. The others fill this in themselves.
    display_name: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str


class SignedInResponse(UserResponse):
    token: str
    expires_at: datetime


class IdentityResponse(BaseModel):
    provider: str
    label: str
    email: str
    connected_at: datetime


def _as_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name}


def _as_identity(row: Identity) -> dict:
    return {
        "provider": row.provider,
        "label": label(row.provider),
        "email": row.email,
        "connected_at": row.created_at,
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


async def _identify(request: SignInRequest) -> identity.ProviderIdentity:
    """Ask the provider who this is, or refuse in the provider's name.

    The reason is logged and not returned: what a provider objected to is
    operator information, and repeating it to the browser tells an attacker
    which half of their guess was wrong.
    """
    try:
        provider = identity.provider(request.provider)
    except identity.IdentityError as error:
        logger.warning("identity.unknown_provider", provider=request.provider,
                       reason=str(error))
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{request.provider} is not a way to sign in"
        ) from error

    try:
        if request.provider == "apple":
            return await provider.identify(
                request.code, request.redirect_uri, request.display_name
            )
        return await provider.identify(request.code, request.redirect_uri)
    except identity.IdentityError as error:
        logger.warning("identity.refused", provider=request.provider, reason=str(error))
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Sign in with {label(request.provider)} did not work, try again",
        ) from error


async def _find(database: AsyncSession, provider: str, subject: str) -> Identity | None:
    return await database.scalar(
        select(Identity).where(
            Identity.provider == provider, Identity.subject == subject
        )
    )


@router.get("/providers")
async def list_providers(redirect_uri: str, state: str = "") -> list[ProviderResponse]:
    """Where to send someone for each way of signing in.

    Built here rather than in each client so that adding a provider does not
    mean shipping a new web, iOS and Android build.
    """
    providers = []
    for name in identity.configured():
        try:
            built = identity.provider(name)
        except identity.IdentityError as error:
            # One provider missing its credentials must not take out the
            # others, and a button that cannot work is worse than no button.
            logger.error("identity.unavailable", provider=name, reason=str(error))
            continue

        providers.append(
            ProviderResponse(
                name=name,
                label=label(name),
                authorization_url=await built.authorization_url(redirect_uri, state),
            )
        )

    return providers


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def sign_in(request: SignInRequest, database: Db) -> SignedInResponse:
    who = await _identify(request)

    existing = await _find(database, request.provider, who.subject)
    if existing is not None:
        user = await database.get(User, existing.user_id)
    else:
        # A first sign-in with this identity opens an account. Deliberately
        # not matched against a user with the same address: gary cannot
        # verify that address, so trusting it would let anyone who can get a
        # provider to assert it walk into someone else's account.
        user = User(email=who.email, display_name=who.display_name)
        database.add(user)
        await database.flush()
        database.add(
            Identity(
                user_id=user.id,
                provider=request.provider,
                subject=who.subject,
                email=who.email,
            )
        )
        await database.commit()

    token, expires_at = await _issue_session(database, user)
    logger.info("auth.signed_in", provider=request.provider, user_id=str(user.id),
                created=existing is None)
    return SignedInResponse(**_as_user(user), token=token, expires_at=expires_at)


@router.delete("/sessions/current", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(database: Db, session: CurrentSession) -> None:
    await database.delete(session)
    await database.commit()


@router.get("/me")
async def read_me(user: CurrentUser) -> UserResponse:
    return UserResponse(**_as_user(user))


@router.patch("/me")
async def update_me(
    request: DisplayName, database: Db, user: CurrentUser
) -> UserResponse:
    user.display_name = request.display_name
    await database.commit()
    return UserResponse(**_as_user(user))


@router.get("/me/identities")
async def list_identities(user: CurrentUser) -> list[IdentityResponse]:
    return [
        IdentityResponse(**_as_identity(row))
        for row in sorted(user.identities, key=lambda row: row.created_at)
    ]


@router.post("/me/identities", status_code=status.HTTP_201_CREATED)
async def connect_identity(
    request: SignInRequest, database: Db, user: CurrentUser
) -> IdentityResponse:
    """Attach another provider to the account already signed in.

    Being signed in is the whole security argument: it proves the same person
    holds both, which is what gary cannot conclude from two matching email
    addresses.
    """
    who = await _identify(request)

    existing = await _find(database, request.provider, who.subject)
    if existing is not None:
        if existing.user_id == user.id:
            # Already yours. Connecting twice is not an error to anyone.
            return IdentityResponse(**_as_identity(existing))

        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"That {label(request.provider)} account is already connected"
            " to another gary account",
        )

    row = Identity(
        user_id=user.id,
        provider=request.provider,
        subject=who.subject,
        email=who.email,
    )
    database.add(row)
    try:
        await database.commit()
    except IntegrityError as error:
        # Lost the race against another request connecting the same identity.
        await database.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"That {label(request.provider)} account is already connected"
            " to another gary account",
        ) from error

    logger.info("auth.identity_connected", provider=request.provider,
                user_id=str(user.id))
    return IdentityResponse(**_as_identity(row))


@router.delete("/me/identities/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_identity(provider: str, database: Db, user: CurrentUser) -> None:
    rows = list(user.identities)
    found = next((row for row in rows if row.provider == provider), None)
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"{label(provider)} is not connected"
        )

    # Removing the last one would leave an account nobody can ever reach —
    # there is no password to fall back on.
    if len(rows) == 1:
        raise HTTPException(status.HTTP_409_CONFLICT, ONLY_WAY_IN)

    await database.delete(found)
    await database.commit()
    logger.info("auth.identity_disconnected", provider=provider, user_id=str(user.id))
