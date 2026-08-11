import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    campaigns: Mapped[list["Campaign"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
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


class Campaign(Base):
    """One game, belonging to one account.

    Everything below it hangs off this, and reaching any of it means reaching
    the campaign first — which is what makes one ownership check enough.
    """

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120))
    # Validated against the registry, not a foreign key: the systems ship with
    # the app rather than living in a table, so there is nothing to point at.
    system_slug: Mapped[str] = mapped_column(String(64))
    module_slug: Mapped[str] = mapped_column(String(64))
    # Which model runs this campaign. Null means whatever the deployment's
    # GM_MODEL says, so a campaign started before models were selectable reads
    # exactly the same way and the default stays a deployment concern.
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="campaigns")
    characters: Mapped[list["Character"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", lazy="selectin"
    )
    turns: Mapped[list["Turn"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    events: Mapped[list["WorldEvent"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Character(Base):
    """The sheet, as it was written.

    Nothing here changes during play. Current hit points and conditions are
    projected from world events instead, so "why is Maud on 3" is answered by
    a list of things that happened rather than by a column somebody
    overwrote — and so the two can never disagree.
    """

    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(80))
    # Spelled the way the system spells it, because the system is asked.
    character_class: Mapped[str] = mapped_column(String(40))
    level: Mapped[int] = mapped_column(Integer, default=1)
    # Keyed by whatever the system calls its abilities, so a system with a
    # different set needs no migration here.
    abilities: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    max_hp: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    campaign: Mapped[Campaign] = relationship(back_populates="characters")


class Turn(Base):
    """One thing said, by a player or by gary."""

    __tablename__ = "turns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(8))
    content: Mapped[str] = mapped_column(Text, default="")
    # False when a turn was cut off — the tab closed, the model fell over.
    # Kept rather than dropped, because the next turn is told the transcript
    # and a hole in it is a story that never happened.
    complete: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    campaign: Mapped[Campaign] = relationship(back_populates="turns")
    rolls: Mapped[list["Roll"]] = relationship(
        back_populates="turn", cascade="all, delete-orphan", lazy="selectin"
    )


class Roll(Base):
    """A roll that really happened, kept beside the turn it happened in.

    The individual dice and not just the total, because "17" and "a 14 and a
    3" are different things to read, and because a natural 20 is worth
    knowing about.
    """

    __tablename__ = "rolls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    turn_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("turns.id", ondelete="CASCADE")
    )
    notation: Mapped[str] = mapped_column(String(32))
    dice: Mapped[list[int]] = mapped_column(JSONB)
    modifier: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120), default="")
    # Set when the roll was a check rather than a bare roll. The degree is
    # whatever the system graded it, so a four-degree system stores four.
    dc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    degree: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    turn: Mapped[Turn] = relationship(back_populates="rolls")


class WorldEvent(Base):
    """Something that became true, and stayed true.

    Append-only, and the only record of world state there is — current state
    is a fold over these rows rather than a column beside them. There is no
    snapshot to drift out of agreement with the log, because there is no
    snapshot.
    """

    __tablename__ = "world_events"
    __table_args__ = (
        # Ordering has to be exact and not merely usually right: two events in
        # the same millisecond that project in the wrong order give a
        # different world. The constraint is what makes a race fail loudly
        # rather than quietly reorder history.
        UniqueConstraint("campaign_id", "seq", name="uq_world_events_campaign_seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Which turn caused it, when a turn did. Null for the events that set a
    # campaign up before anybody has said anything.
    turn_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("turns.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    campaign: Mapped[Campaign] = relationship(back_populates="events")
