"""Tables. Everything a Chog does is keyed by chog_id, never by wallet alone."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Chog(Base):
    __tablename__ = "chogs"
    __table_args__ = (UniqueConstraint("collection", "token_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    collection: Mapped[str] = mapped_column(String(42))
    token_id: Mapped[int] = mapped_column(Integer)
    current_owner: Mapped[str | None] = mapped_column(String(42))
    owner_count: Mapped[int] = mapped_column(Integer, default=0)
    traits: Mapped[dict] = mapped_column(JSON, default=dict)
    last_synced: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    wallet: Mapped[str] = mapped_column(String(42), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthNonce(Base):
    __tablename__ = "auth_nonces"

    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    kind: Mapped[str] = mapped_column(String(20), default="online")  # online | irl | spaces | discord
    visibility: Mapped[str] = mapped_column(String(20), default="holder")  # public | holder
    official: Mapped[bool] = mapped_column(Boolean, default=True)
    capacity: Mapped[int | None] = mapped_column(Integer)
    prize_text: Mapped[str | None] = mapped_column(String(200))
    link: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[str | None] = mapped_column(String(42))

    participations: Mapped[list["EventParticipation"]] = relationship(back_populates="event")


class EventParticipation(Base):
    __tablename__ = "event_participations"
    __table_args__ = (UniqueConstraint("event_id", "chog_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    chog_id: Mapped[int] = mapped_column(ForeignKey("chogs.id"))
    wallet: Mapped[str] = mapped_column(String(42))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    onchain_tx: Mapped[str | None] = mapped_column(String(66))

    event: Mapped[Event] = relationship(back_populates="participations")


class EventRSVP(Base):
    """A wallet joining an "Everyone" event without a Chog. No on-chain record:
    reputation belongs to Chogs, so only Chog joins count towards it."""

    __tablename__ = "event_rsvps"
    __table_args__ = (UniqueConstraint("event_id", "wallet"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    wallet: Mapped[str] = mapped_column(String(42))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(16), default="trophy")
    kind: Mapped[str] = mapped_column(String(20), default="quest")  # quest | win | contribution


class Quest(Base):
    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # manual: admin reviews proof | auto_buy: verified from a confirmed buy | auto_event: joined the linked event
    verify_type: Mapped[str] = mapped_column(String(20), default="manual")
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"))
    trait_requirement: Mapped[dict | None] = mapped_column(JSON)  # e.g. {"hat": "Pirate Hat"}
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    achievement: Mapped[Achievement] = relationship()
    event: Mapped["Event | None"] = relationship()


class QuestSubmission(Base):
    __tablename__ = "quest_submissions"
    __table_args__ = (UniqueConstraint("quest_id", "chog_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quest_id: Mapped[int] = mapped_column(ForeignKey("quests.id"))
    chog_id: Mapped[int] = mapped_column(ForeignKey("chogs.id"))
    wallet: Mapped[str] = mapped_column(String(42))
    proof_text: Mapped[str | None] = mapped_column(Text)
    proof_url: Mapped[str | None] = mapped_column(String(500))
    # in_progress | submitted | approved | rejected
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    reviewed_by: Mapped[str | None] = mapped_column(String(42))
    onchain_tx: Mapped[str | None] = mapped_column(String(66))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    quest: Mapped[Quest] = relationship()


class AgentMemory(Base):
    """Private memory: belongs to (Chog, owner). A new owner starts fresh."""

    __tablename__ = "agent_memory"
    __table_args__ = (UniqueConstraint("chog_id", "owner_wallet"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chog_id: Mapped[int] = mapped_column(ForeignKey("chogs.id"))
    owner_wallet: Mapped[str] = mapped_column(String(42))
    summary: Mapped[str] = mapped_column(Text, default="")
    prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    greeted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PendingAction(Base):
    """State behind a confirm card: prepared -> sent -> confirmed | failed | expired."""

    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chog_id: Mapped[int] = mapped_column(ForeignKey("chogs.id"))
    wallet: Mapped[str] = mapped_column(String(42))
    kind: Mapped[str] = mapped_column(String(30))  # buy_chog
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    unsigned_tx: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="prepared")
    tx_hash: Mapped[str | None] = mapped_column(String(66))
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
