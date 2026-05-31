"""Repository helpers for database access.

The services layer should depend on these small async repositories instead of writing
SQLAlchemy queries inside Discord command handlers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import TicketEventType, TicketStatus
from bot.database.models import (
    GuildSettings,
    SupportRole,
    Ticket,
    TicketAttachment,
    TicketEvent,
    UserTicketChannel,
)


class GuildSettingsRepository:
    """Data access for per-guild settings."""

    async def get_by_guild_id(
        self,
        session: AsyncSession,
        guild_id: int,
    ) -> GuildSettings | None:
        result = await session.execute(
            select(GuildSettings).where(GuildSettings.guild_id == guild_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        category_id: int | None = None,
        support_channel_id: int | None = None,
        logs_channel_id: int | None = None,
        settings_channel_id: int | None = None,
        support_message_id: int | None = None,
        settings_message_id: int | None = None,
        locale: str = "en",
        category_name: str = "Tickets! Please",
        support_channel_name: str = "support",
        logs_channel_name: str = "tickets-logs",
        settings_channel_name: str = "tickets-settings",
        is_enabled: bool = True,
    ) -> GuildSettings:
        settings = GuildSettings(
            guild_id=guild_id,
            category_id=category_id,
            support_channel_id=support_channel_id,
            logs_channel_id=logs_channel_id,
            settings_channel_id=settings_channel_id,
            support_message_id=support_message_id,
            settings_message_id=settings_message_id,
            locale=locale,
            category_name=category_name,
            support_channel_name=support_channel_name,
            logs_channel_name=logs_channel_name,
            settings_channel_name=settings_channel_name,
            is_enabled=is_enabled,
        )
        session.add(settings)
        await session.flush()
        return settings

    async def update(
        self,
        session: AsyncSession,
        settings: GuildSettings,
        **fields: int | str | bool | None,
    ) -> GuildSettings:
        for field_name, value in fields.items():
            setattr(settings, field_name, value)
        await session.flush()
        return settings

    async def delete_by_guild_id(self, session: AsyncSession, guild_id: int) -> bool:
        settings = await self.get_by_guild_id(session, guild_id)
        if settings is None:
            return False

        await session.delete(settings)
        await session.flush()
        return True


class SupportRoleRepository:
    """Data access for guild support roles."""

    async def list_for_guild(self, session: AsyncSession, guild_id: int) -> list[SupportRole]:
        result = await session.execute(
            select(SupportRole)
            .where(SupportRole.guild_id == guild_id)
            .order_by(SupportRole.created_at.asc())
        )
        return list(result.scalars())

    async def add(self, session: AsyncSession, *, guild_id: int, role_id: int) -> SupportRole:
        existing = await session.execute(
            select(SupportRole).where(
                SupportRole.guild_id == guild_id,
                SupportRole.role_id == role_id,
            )
        )
        role = existing.scalar_one_or_none()
        if role is not None:
            return role

        role = SupportRole(guild_id=guild_id, role_id=role_id)
        session.add(role)
        await session.flush()
        return role

    async def remove(self, session: AsyncSession, *, guild_id: int, role_id: int) -> None:
        await session.execute(
            delete(SupportRole).where(
                SupportRole.guild_id == guild_id,
                SupportRole.role_id == role_id,
            )
        )

    async def clear_for_guild(self, session: AsyncSession, guild_id: int) -> None:
        await session.execute(delete(SupportRole).where(SupportRole.guild_id == guild_id))


class UserTicketChannelRepository:
    """Data access for private per-user ticket channels."""

    async def get(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
    ) -> UserTicketChannel | None:
        result = await session.execute(
            select(UserTicketChannel).where(
                UserTicketChannel.guild_id == guild_id,
                UserTicketChannel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
        channel_id: int,
    ) -> UserTicketChannel:
        record = await self.get(session, guild_id=guild_id, user_id=user_id)
        if record is None:
            record = UserTicketChannel(
                guild_id=guild_id,
                user_id=user_id,
                channel_id=channel_id,
            )
            session.add(record)
        else:
            record.channel_id = channel_id

        await session.flush()
        return record

    async def list_for_guild(self, session: AsyncSession, guild_id: int) -> list[UserTicketChannel]:
        result = await session.execute(
            select(UserTicketChannel)
            .where(UserTicketChannel.guild_id == guild_id)
            .order_by(UserTicketChannel.created_at.asc())
        )
        return list(result.scalars())


class TicketRepository:
    """Data access for ticket lifecycle records."""

    async def next_ticket_number(self, session: AsyncSession, guild_id: int) -> int:
        result = await session.execute(
            select(func.coalesce(func.max(Ticket.ticket_number), 0) + 1).where(
                Ticket.guild_id == guild_id
            )
        )
        return int(result.scalar_one())

    async def create(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
        channel_id: int,
        thread_id: int,
        ticket_number: int,
        title: str,
        description: str,
        log_thread_id: int | None = None,
    ) -> Ticket:
        ticket = Ticket(
            guild_id=guild_id,
            user_id=user_id,
            channel_id=channel_id,
            thread_id=thread_id,
            log_thread_id=log_thread_id,
            ticket_number=ticket_number,
            title=title,
            description=description,
        )
        session.add(ticket)
        await session.flush()
        return ticket

    async def get_by_id(self, session: AsyncSession, ticket_id: int) -> Ticket | None:
        result = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()

    async def get_by_thread_id(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        thread_id: int,
    ) -> Ticket | None:
        result = await session.execute(
            select(Ticket).where(Ticket.guild_id == guild_id, Ticket.thread_id == thread_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
        limit: int = 20,
    ) -> list[Ticket]:
        result = await session.execute(
            select(Ticket)
            .where(Ticket.guild_id == guild_id, Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def list_open_for_user(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
        limit: int = 10,
    ) -> list[Ticket]:
        result = await session.execute(
            select(Ticket)
            .where(
                Ticket.guild_id == guild_id,
                Ticket.user_id == user_id,
                Ticket.status != TicketStatus.CLOSED,
            )
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def list_closed_for_user(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
        limit: int = 5,
    ) -> list[Ticket]:
        result = await session.execute(
            select(Ticket)
            .where(
                Ticket.guild_id == guild_id,
                Ticket.user_id == user_id,
                Ticket.status == TicketStatus.CLOSED,
            )
            .order_by(Ticket.closed_at.desc(), Ticket.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def count_open_for_user(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
    ) -> int:
        result = await session.execute(
            select(func.count(Ticket.id)).where(
                Ticket.guild_id == guild_id,
                Ticket.user_id == user_id,
                Ticket.status != TicketStatus.CLOSED,
            )
        )
        return int(result.scalar_one())

    async def assign_moderator(
        self,
        session: AsyncSession,
        ticket: Ticket,
        *,
        moderator_id: int,
    ) -> Ticket:
        ticket.assigned_moderator_id = moderator_id
        ticket.status = TicketStatus.IN_PROGRESS
        await session.flush()
        return ticket

    async def set_log_thread_id(
        self,
        session: AsyncSession,
        ticket_id: int,
        *,
        log_thread_id: int,
    ) -> Ticket | None:
        ticket = await self.get_by_id(session, ticket_id)
        if ticket is None:
            return None

        ticket.log_thread_id = log_thread_id
        await session.flush()
        return ticket

    async def close(
        self,
        session: AsyncSession,
        ticket: Ticket,
        *,
        closed_by_id: int,
        close_reason: str,
    ) -> Ticket:
        ticket.status = TicketStatus.CLOSED
        ticket.closed_by_id = closed_by_id
        ticket.close_reason = close_reason
        ticket.closed_at = datetime.now(UTC)
        await session.flush()
        return ticket


class TicketAttachmentRepository:
    """Data access for ticket attachment metadata."""

    async def create(
        self,
        session: AsyncSession,
        *,
        ticket_id: int,
        filename: str,
        url: str,
        content_type: str | None = None,
        size: int | None = None,
    ) -> TicketAttachment:
        attachment = TicketAttachment(
            ticket_id=ticket_id,
            filename=filename,
            url=url,
            content_type=content_type,
            size=size,
        )
        session.add(attachment)
        await session.flush()
        return attachment


class TicketEventRepository:
    """Data access for append-only ticket events."""

    async def create(
        self,
        session: AsyncSession,
        *,
        ticket_id: int,
        event_type: TicketEventType,
        actor_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TicketEvent:
        event = TicketEvent(
            ticket_id=ticket_id,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload or {},
        )
        session.add(event)
        await session.flush()
        return event
