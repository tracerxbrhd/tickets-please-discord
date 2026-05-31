"""Ticket lifecycle and support panel service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

import hikari
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import TicketEventType, TicketStatus
from bot.database.models import GuildSettings, Ticket
from bot.database.repositories import (
    GuildSettingsRepository,
    SupportRoleRepository,
    TicketEventRepository,
    TicketRepository,
    UserTicketChannelRepository,
)
from bot.i18n import DEFAULT_LOCALE, t
from bot.utils.formatters import ticket_thread_name, user_ticket_channel_name
from bot.utils.limits import MAX_OPEN_TICKETS_PER_USER
from bot.utils.permissions import user_ticket_channel_overwrites

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PanelValidationResult:
    """Validation result for a support panel component interaction."""

    is_valid: bool
    reason: str | None = None
    settings: GuildSettings | None = None


@dataclass(slots=True)
class TicketCreationPrompt:
    """Validation result used before opening the create-ticket modal."""

    validation: PanelValidationResult


@dataclass(slots=True)
class UserTicketList:
    """Tickets shown to a user from the support panel."""

    validation: PanelValidationResult
    open_tickets: list[Ticket]
    closed_tickets: list[Ticket]


@dataclass(slots=True)
class TicketCreationResult:
    """Result of creating a Discord ticket thread and DB record."""

    validation: PanelValidationResult
    ticket: Ticket | None = None
    user_channel_id: int | None = None
    thread_id: int | None = None
    user_channel_created: bool = False
    support_role_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class TicketCloseValidationResult:
    """Validation result used before opening or applying ticket closure."""

    is_valid: bool
    reason: str | None = None
    ticket: Ticket | None = None
    settings: GuildSettings | None = None


@dataclass(slots=True)
class TicketClaimValidationResult:
    """Validation result for assigning a moderator to a ticket."""

    is_valid: bool
    reason: str | None = None
    ticket: Ticket | None = None
    settings: GuildSettings | None = None


@dataclass(slots=True)
class TicketCloseResult:
    """Result of closing a ticket."""

    validation: TicketCloseValidationResult
    ticket: Ticket | None = None


@dataclass(slots=True)
class TicketClaimResult:
    """Result of claiming a ticket for moderation work."""

    validation: TicketClaimValidationResult
    ticket: Ticket | None = None


@dataclass(slots=True)
class TicketMessageLogContext:
    """Resolved ticket context for message mirroring into the log thread."""

    ticket: Ticket
    settings: GuildSettings | None


class TicketService:
    """Service API for ticket-facing support panel actions."""

    def __init__(
        self,
        settings_repository: GuildSettingsRepository | None = None,
        ticket_repository: TicketRepository | None = None,
        user_channel_repository: UserTicketChannelRepository | None = None,
        support_role_repository: SupportRoleRepository | None = None,
        ticket_event_repository: TicketEventRepository | None = None,
    ) -> None:
        self._settings_repository = settings_repository or GuildSettingsRepository()
        self._ticket_repository = ticket_repository or TicketRepository()
        self._user_channel_repository = user_channel_repository or UserTicketChannelRepository()
        self._support_role_repository = support_role_repository or SupportRoleRepository()
        self._ticket_event_repository = ticket_event_repository or TicketEventRepository()

    async def prepare_ticket_creation(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        user_id: int,
    ) -> TicketCreationPrompt:
        """Validate panel context before ticket creation starts."""

        validation = await self._validate_panel_context(
            session,
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
        )
        if validation.is_valid:
            validation = await self._validate_open_ticket_limit(
                session,
                guild_id=guild_id,
                user_id=user_id,
                settings=validation.settings,
            )
        return TicketCreationPrompt(validation=validation)

    async def list_user_tickets(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        user_id: int,
        open_limit: int = 6,
        closed_limit: int = 6,
    ) -> UserTicketList:
        """Return recent user tickets after validating the support panel context."""

        validation = await self._validate_panel_context(
            session,
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
        )
        if not validation.is_valid:
            return UserTicketList(validation=validation, open_tickets=[], closed_tickets=[])

        open_tickets = await self._ticket_repository.list_open_for_user(
            session,
            guild_id=guild_id,
            user_id=user_id,
            limit=open_limit,
        )
        closed_tickets = await self._ticket_repository.list_closed_for_user(
            session,
            guild_id=guild_id,
            user_id=user_id,
            limit=closed_limit,
        )
        return UserTicketList(
            validation=validation,
            open_tickets=open_tickets,
            closed_tickets=closed_tickets,
        )

    async def create_ticket(
        self,
        session: AsyncSession,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        panel_channel_id: int,
        panel_message_id: int,
        user_id: int,
        user_name: str | None,
        title: str,
        description: str,
    ) -> TicketCreationResult:
        """Create a new ticket channel thread and persist the ticket record."""

        validation = await self._validate_panel_context(
            session,
            guild_id=guild_id,
            channel_id=panel_channel_id,
            message_id=panel_message_id,
        )
        if not validation.is_valid:
            return TicketCreationResult(validation=validation)

        validation = await self._validate_open_ticket_limit(
            session,
            guild_id=guild_id,
            user_id=user_id,
            settings=validation.settings,
        )
        if not validation.is_valid:
            return TicketCreationResult(validation=validation)

        settings = validation.settings
        locale = settings.locale if settings else DEFAULT_LOCALE
        if settings is None or settings.category_id is None:
            return TicketCreationResult(
                validation=PanelValidationResult(
                    is_valid=False,
                    reason=t(locale, "ticket.category_missing"),
                    settings=settings,
                )
            )

        bot_user = await rest.fetch_my_user()
        support_roles = await self._support_role_repository.list_for_guild(session, guild_id)
        support_role_ids = [role.role_id for role in support_roles]
        user_channel, channel_created = await self._get_or_create_user_channel(
            session,
            rest,
            guild_id=guild_id,
            user_id=user_id,
            user_name=user_name,
            bot_user_id=int(bot_user.id),
            category_id=settings.category_id,
            support_role_ids=support_role_ids,
        )
        ticket_number = await self._ticket_repository.next_ticket_number(session, guild_id)
        thread = await rest.create_thread(
            int(user_channel.id),
            hikari.ChannelType.GUILD_PUBLIC_THREAD,
            ticket_thread_name(ticket_number, title),
            auto_archive_duration=timedelta(days=7),
        )
        ticket = await self._ticket_repository.create(
            session,
            guild_id=guild_id,
            user_id=user_id,
            channel_id=int(user_channel.id),
            thread_id=int(thread.id),
            ticket_number=ticket_number,
            title=title,
            description=description,
        )
        await self._ticket_event_repository.create(
            session,
            ticket_id=ticket.id,
            event_type=TicketEventType.TICKET_CREATED,
            actor_id=user_id,
            payload={
                "channel_id": int(user_channel.id),
                "thread_id": int(thread.id),
                "title": title,
            },
        )

        return TicketCreationResult(
            validation=validation,
            ticket=ticket,
            user_channel_id=int(user_channel.id),
            thread_id=int(thread.id),
            user_channel_created=channel_created,
            support_role_ids=support_role_ids,
        )

    async def set_ticket_log_thread(
        self,
        session: AsyncSession,
        *,
        ticket_id: int,
        log_thread_id: int,
    ) -> Ticket | None:
        """Persist the logs-channel thread linked to a ticket."""

        return await self._ticket_repository.set_log_thread_id(
            session,
            ticket_id,
            log_thread_id=log_thread_id,
        )

    async def get_message_log_context(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        thread_id: int,
        author_id: int,
    ) -> TicketMessageLogContext | None:
        """Return a loggable claimed-ticket context for a thread message."""

        ticket = await self._ticket_repository.get_by_thread_id(
            session,
            guild_id=guild_id,
            thread_id=thread_id,
        )
        if ticket is None:
            return None
        if ticket.status == TicketStatus.CLOSED or ticket.assigned_moderator_id is None:
            return None
        if author_id not in {ticket.user_id, ticket.assigned_moderator_id}:
            return None

        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        return TicketMessageLogContext(ticket=ticket, settings=settings)

    async def validate_ticket_claim(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        thread_id: int,
        actor_id: int,
        actor_role_ids: set[int],
        actor_permissions: hikari.Permissions,
    ) -> TicketClaimValidationResult:
        """Validate that a moderator may claim the ticket for work."""

        ticket = await self._ticket_repository.get_by_thread_id(
            session,
            guild_id=guild_id,
            thread_id=thread_id,
        )
        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        locale = settings.locale if settings else DEFAULT_LOCALE
        if ticket is None:
            return TicketClaimValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.thread_not_linked"),
                settings=settings,
            )

        if ticket.status == TicketStatus.CLOSED:
            return TicketClaimValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.already_closed"),
                ticket=ticket,
                settings=settings,
            )

        support_roles = await self._support_role_repository.list_for_guild(session, guild_id)
        support_role_ids = {role.role_id for role in support_roles}
        if not self._can_manage_ticket(
            actor_role_ids=actor_role_ids,
            support_role_ids=support_role_ids,
            actor_permissions=actor_permissions,
        ):
            return TicketClaimValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.claim_forbidden"),
                ticket=ticket,
                settings=settings,
            )

        if ticket.assigned_moderator_id is not None:
            return TicketClaimValidationResult(
                is_valid=False,
                reason=t(
                    locale,
                    "ticket.already_claimed",
                    moderator_id=ticket.assigned_moderator_id,
                ),
                ticket=ticket,
                settings=settings,
            )

        return TicketClaimValidationResult(is_valid=True, ticket=ticket, settings=settings)

    async def claim_ticket(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        thread_id: int,
        actor_id: int,
        actor_role_ids: set[int],
        actor_permissions: hikari.Permissions,
    ) -> TicketClaimResult:
        """Assign the ticket to a moderator and move it to in-progress."""

        validation = await self.validate_ticket_claim(
            session,
            guild_id=guild_id,
            thread_id=thread_id,
            actor_id=actor_id,
            actor_role_ids=actor_role_ids,
            actor_permissions=actor_permissions,
        )
        if not validation.is_valid or validation.ticket is None:
            return TicketClaimResult(validation=validation)

        ticket = await self._ticket_repository.assign_moderator(
            session,
            validation.ticket,
            moderator_id=actor_id,
        )
        await self._ticket_event_repository.create(
            session,
            ticket_id=ticket.id,
            event_type=TicketEventType.TICKET_CLAIMED,
            actor_id=actor_id,
            payload={
                "thread_id": ticket.thread_id,
                "moderator_id": actor_id,
            },
        )
        return TicketClaimResult(validation=validation, ticket=ticket)

    async def validate_ticket_close(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        thread_id: int,
        actor_id: int,
        actor_role_ids: set[int],
        actor_permissions: hikari.Permissions,
    ) -> TicketCloseValidationResult:
        """Validate that an actor may close the ticket for a thread."""

        ticket = await self._ticket_repository.get_by_thread_id(
            session,
            guild_id=guild_id,
            thread_id=thread_id,
        )
        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        if ticket is None:
            return TicketCloseValidationResult(
                is_valid=False,
                reason=t(
                    settings.locale if settings else DEFAULT_LOCALE,
                    "ticket.thread_not_linked",
                ),
                settings=settings,
            )

        locale = settings.locale if settings else DEFAULT_LOCALE
        if ticket.status == TicketStatus.CLOSED:
            return TicketCloseValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.already_closed"),
                ticket=ticket,
                settings=settings,
            )

        support_roles = await self._support_role_repository.list_for_guild(session, guild_id)
        support_role_ids = {role.role_id for role in support_roles}
        if not self._can_close_ticket(
            ticket,
            actor_id=actor_id,
            actor_role_ids=actor_role_ids,
            support_role_ids=support_role_ids,
            actor_permissions=actor_permissions,
        ):
            return TicketCloseValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.close_forbidden"),
                ticket=ticket,
                settings=settings,
            )

        return TicketCloseValidationResult(
            is_valid=True,
            ticket=ticket,
            settings=settings,
        )

    async def close_ticket(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        thread_id: int,
        actor_id: int,
        actor_role_ids: set[int],
        actor_permissions: hikari.Permissions,
        close_reason: str,
    ) -> TicketCloseResult:
        """Close a ticket permanently in the database."""

        validation = await self.validate_ticket_close(
            session,
            guild_id=guild_id,
            thread_id=thread_id,
            actor_id=actor_id,
            actor_role_ids=actor_role_ids,
            actor_permissions=actor_permissions,
        )
        if not validation.is_valid or validation.ticket is None:
            return TicketCloseResult(validation=validation)

        ticket = await self._ticket_repository.close(
            session,
            validation.ticket,
            closed_by_id=actor_id,
            close_reason=close_reason,
        )
        await self._ticket_event_repository.create(
            session,
            ticket_id=ticket.id,
            event_type=TicketEventType.TICKET_CLOSED,
            actor_id=actor_id,
            payload={
                "thread_id": ticket.thread_id,
                "reason": close_reason,
            },
        )
        return TicketCloseResult(validation=validation, ticket=ticket)

    async def _validate_panel_context(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
    ) -> PanelValidationResult:
        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        if settings is None:
            return PanelValidationResult(
                is_valid=False,
                reason=t(DEFAULT_LOCALE, "ticket.system_not_configured"),
            )

        locale = settings.locale
        if not settings.is_enabled:
            return PanelValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.system_disabled"),
                settings=settings,
            )

        if settings.support_channel_id != channel_id or settings.support_message_id != message_id:
            return PanelValidationResult(
                is_valid=False,
                reason=t(locale, "ticket.support_panel_stale"),
                settings=settings,
            )

        return PanelValidationResult(is_valid=True, settings=settings)

    async def _validate_open_ticket_limit(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        user_id: int,
        settings: GuildSettings | None,
    ) -> PanelValidationResult:
        open_ticket_count = await self._ticket_repository.count_open_for_user(
            session,
            guild_id=guild_id,
            user_id=user_id,
        )
        if open_ticket_count >= MAX_OPEN_TICKETS_PER_USER:
            return PanelValidationResult(
                is_valid=False,
                reason=t(
                    settings.locale if settings else DEFAULT_LOCALE,
                    "ticket.limit_reached",
                    limit=MAX_OPEN_TICKETS_PER_USER,
                ),
                settings=settings,
            )

        return PanelValidationResult(is_valid=True, settings=settings)

    async def _get_or_create_user_channel(
        self,
        session: AsyncSession,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        user_id: int,
        user_name: str | None,
        bot_user_id: int,
        category_id: int,
        support_role_ids: list[int],
    ) -> tuple[hikari.GuildTextChannel, bool]:
        existing_record = await self._user_channel_repository.get(
            session,
            guild_id=guild_id,
            user_id=user_id,
        )
        if existing_record is not None:
            channel = await self._fetch_user_channel(rest, existing_record.channel_id)
            if channel is not None:
                return channel, False

        channel = await rest.create_guild_text_channel(
            guild_id,
            name=user_ticket_channel_name(user_name, user_id=user_id),
            category=category_id,
            permission_overwrites=user_ticket_channel_overwrites(
                guild_id=guild_id,
                user_id=user_id,
                bot_user_id=bot_user_id,
                support_role_ids=support_role_ids,
            ),
        )
        await self._user_channel_repository.upsert(
            session,
            guild_id=guild_id,
            user_id=user_id,
            channel_id=int(channel.id),
        )
        return channel, True

    async def _fetch_user_channel(
        self,
        rest: hikari.api.RESTClient,
        channel_id: int,
    ) -> hikari.GuildTextChannel | None:
        try:
            channel = await rest.fetch_channel(channel_id)
        except hikari.NotFoundError:
            return None
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to fetch stored ticket channel %s", channel_id)
            return None

        if isinstance(channel, hikari.GuildTextChannel):
            return channel

        LOGGER.warning("Stored ticket channel %s is not a guild text channel", channel_id)
        return None

    def _can_close_ticket(
        self,
        ticket: Ticket,
        *,
        actor_id: int,
        actor_role_ids: set[int],
        support_role_ids: set[int],
        actor_permissions: hikari.Permissions,
    ) -> bool:
        if actor_id == ticket.user_id:
            return True
        if actor_permissions & hikari.Permissions.ADMINISTRATOR:
            return True
        if self._can_manage_ticket(
            actor_role_ids=actor_role_ids,
            support_role_ids=support_role_ids,
            actor_permissions=actor_permissions,
        ):
            return True
        return bool(actor_role_ids & support_role_ids)

    def _can_manage_ticket(
        self,
        *,
        actor_role_ids: set[int],
        support_role_ids: set[int],
        actor_permissions: hikari.Permissions,
    ) -> bool:
        if actor_permissions & hikari.Permissions.ADMINISTRATOR:
            return True
        if actor_permissions & (
            hikari.Permissions.MANAGE_GUILD
            | hikari.Permissions.MANAGE_CHANNELS
            | hikari.Permissions.MANAGE_THREADS
        ):
            return True
        return bool(actor_role_ids & support_role_ids)
