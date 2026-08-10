import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # The address from whichever identity opened the account. Deliberately not
    # unique and never used to find anyone: an address gary has not verified
    # itself is not something it can safely key on. Identities are.
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    identities: Mapped[list["Identity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class Identity(Base):
    """One way of proving you are a particular user.

    An account has many — that is the point of connecting a second provider —
    so the pair (provider, subject) is what sign-in looks up, never the email.
    """

    __tablename__ = "identities"
    __table_args__ = (
        # The constraint, rather than a check in the endpoint, is what stops
        # one provider account reaching two gary accounts. Two requests racing
        # would both pass a check; only one survives this.
        UniqueConstraint("provider", "subject", name="uq_identities_provider_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(32))
    # The provider's own identifier. Stable across their email changes, which
    # is exactly why it and not the address is the key.
    subject: Mapped[str] = mapped_column(String(255))
    # What this provider said the address was. Held per identity because the
    # three will disagree — Apple in particular hands out a relay.
    email: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="identities")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    # The token itself is never stored. A database copy is then not enough to
    # impersonate anyone.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")
