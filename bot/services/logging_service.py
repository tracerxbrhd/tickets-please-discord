"""Ticket event logging service."""

from __future__ import annotations

import logging
from datetime import timedelta

import hikari

from bot.database.models import Ticket
from bot.i18n import DEFAULT_LOCALE
from bot.ui.embeds import (
    build_log_embed,
    build_ticket_claimed_log_embed,
    build_ticket_closed_log_embed,
    build_ticket_created_log_embed,
)
from bot.utils.formatters import ticket_log_thread_name

LOGGER = logging.getLogger(__name__)


class LoggingService:
    """Sends operational events to the configured logs channel."""

    async def send_system_event(
        self,
        rest: hikari.api.RESTClient,
        *,
        logs_channel_id: int | None,
        event_type: str,
        actor_id: int,
        description: str,
    ) -> None:
        """Send a non-blocking log event when a logs channel is available."""

        if logs_channel_id is None:
            return

        try:
            await rest.create_message(
                logs_channel_id,
                embed=build_log_embed(
                    event_type=event_type,
                    actor_id=actor_id,
                    description=description,
                ),
            )
        except hikari.NotFoundError:
            LOGGER.warning("Configured logs channel %s was not found", logs_channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to write to logs channel %s", logs_channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected system log event %s", event_type)

    async def send_ticket_created(
        self,
        rest: hikari.api.RESTClient,
        *,
        logs_channel_id: int | None,
        ticket: Ticket,
        guild_id: int,
        locale: str = DEFAULT_LOCALE,
    ) -> int | None:
        """Send a ticket-created log event and create its log thread."""

        if logs_channel_id is None:
            return None

        try:
            message = await rest.create_message(
                logs_channel_id,
                embed=build_ticket_created_log_embed(
                    ticket,
                    guild_id=guild_id,
                    locale=locale,
                ),
            )
            thread = await rest.create_message_thread(
                logs_channel_id,
                message.id,
                ticket_log_thread_name(ticket.ticket_number, ticket.title),
                auto_archive_duration=timedelta(days=7),
            )
            await rest.create_message(
                int(thread.id),
                content=f"<@{ticket.user_id}>",
                embed=build_ticket_created_log_embed(
                    ticket,
                    guild_id=guild_id,
                    locale=locale,
                ),
                user_mentions=[ticket.user_id],
            )
            return int(thread.id)
        except hikari.NotFoundError:
            LOGGER.warning("Configured logs channel %s was not found", logs_channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to write to logs channel %s", logs_channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected ticket-created log for ticket %s", ticket.id)
        return None

    async def send_ticket_claimed(
        self,
        rest: hikari.api.RESTClient,
        *,
        logs_channel_id: int | None,
        ticket: Ticket,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        """Send a ticket-claimed event to the ticket log thread."""

        if ticket.assigned_moderator_id is None:
            return

        target_channel_id = ticket.log_thread_id or logs_channel_id
        if target_channel_id is None:
            return

        try:
            await rest.create_message(
                target_channel_id,
                content=f"<@{ticket.assigned_moderator_id}>",
                embed=build_ticket_claimed_log_embed(ticket, locale=locale),
                user_mentions=[ticket.assigned_moderator_id],
            )
        except hikari.NotFoundError:
            LOGGER.warning("Configured ticket log thread %s was not found", target_channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to write to ticket log thread %s", target_channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected ticket-claimed log for ticket %s", ticket.id)

    async def send_ticket_closed(
        self,
        rest: hikari.api.RESTClient,
        *,
        logs_channel_id: int | None,
        ticket: Ticket,
        guild_id: int,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        """Send a ticket-closed event to the ticket log thread."""

        target_channel_id = ticket.log_thread_id or logs_channel_id
        if target_channel_id is None:
            return

        try:
            await rest.create_message(
                target_channel_id,
                content=f"<@{ticket.closed_by_id}>" if ticket.closed_by_id is not None else None,
                embed=build_ticket_closed_log_embed(
                    ticket,
                    guild_id=guild_id,
                    locale=locale,
                ),
                user_mentions=[ticket.closed_by_id] if ticket.closed_by_id is not None else [],
            )
            if ticket.log_thread_id is not None:
                await rest.edit_channel(ticket.log_thread_id, archived=True, locked=True)
        except hikari.NotFoundError:
            LOGGER.warning("Configured ticket log thread %s was not found", target_channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to write to ticket log thread %s", target_channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected ticket-closed log for ticket %s", ticket.id)
