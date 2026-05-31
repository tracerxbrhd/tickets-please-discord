"""SQLAlchemy ORM models for the ticket system."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base
from bot.database.enums import TicketEventType, TicketStatus


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]


TICKET_STATUS_ENUM = Enum(
    TicketStatus,
    name="ticket_status",
    values_callable=_enum_values,
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
TICKET_EVENT_TYPE_ENUM = Enum(
    TicketEventType,
    name="ticket_event_type",
    values_callable=_enum_values,
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)


class TimestampMixin:
    """Common timestamp columns for mutable records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    """Common timestamp column for append-only records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class GuildSettings(TimestampMixin, Base):
    """Per-guild ticket system configuration."""

    __tablename__ = "guild_settings"
    __table_args__ = (UniqueConstraint("guild_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category_id: Mapped[int | None] = mapped_column(BigInteger)
    support_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    logs_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    settings_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    support_message_id: Mapped[int | None] = mapped_column(BigInteger)
    settings_message_id: Mapped[int | None] = mapped_column(BigInteger)
    locale: Mapped[str] = mapped_column(String(12), default="en", server_default="en")
    category_name: Mapped[str] = mapped_column(
        String(100),
        default="Tickets! Please",
        server_default="Tickets! Please",
    )
    support_channel_name: Mapped[str] = mapped_column(
        String(100),
        default="support",
        server_default="support",
    )
    logs_channel_name: Mapped[str] = mapped_column(
        String(100),
        default="tickets-logs",
        server_default="tickets-logs",
    )
    settings_channel_name: Mapped[str] = mapped_column(
        String(100),
        default="tickets-settings",
        server_default="tickets-settings",
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class SupportRole(CreatedAtMixin, Base):
    """Support role allowed to see and process tickets in a guild."""

    __tablename__ = "support_roles"
    __table_args__ = (UniqueConstraint("guild_id", "role_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class UserTicketChannel(TimestampMixin, Base):
    """Private ticket parent channel assigned to a user."""

    __tablename__ = "user_ticket_channels"
    __table_args__ = (
        UniqueConstraint("guild_id", "user_id"),
        UniqueConstraint("guild_id", "channel_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Ticket(CreatedAtMixin, Base):
    """Support request created by a guild member."""

    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("guild_id", "ticket_number"),
        UniqueConstraint("guild_id", "thread_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    thread_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    log_thread_id: Mapped[int | None] = mapped_column(BigInteger)
    ticket_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        TICKET_STATUS_ENUM,
        default=TicketStatus.OPEN,
        server_default=TicketStatus.OPEN.value,
        index=True,
        nullable=False,
    )
    assigned_moderator_id: Mapped[int | None] = mapped_column(BigInteger)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_id: Mapped[int | None] = mapped_column(BigInteger)
    close_reason: Mapped[str | None] = mapped_column(Text)

    attachments: Mapped[list[TicketAttachment]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events: Mapped[list[TicketEvent]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TicketAttachment(CreatedAtMixin, Base):
    """Attachment metadata linked to a ticket."""

    __tablename__ = "ticket_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    size: Mapped[int | None] = mapped_column(BigInteger)

    ticket: Mapped[Ticket] = relationship(back_populates="attachments")


class TicketEvent(CreatedAtMixin, Base):
    """Append-only ticket history event."""

    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[TicketEventType] = mapped_column(
        TICKET_EVENT_TYPE_ENUM,
        nullable=False,
    )
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    ticket: Mapped[Ticket] = relationship(back_populates="events")
