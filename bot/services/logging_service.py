"""Ticket event logging service."""

from __future__ import annotations

import logging

import hikari

from bot.database.models import Ticket
from bot.i18n import DEFAULT_LOCALE
from bot.ui.embeds import (
    build_log_embed,
    build_ticket_closed_log_embed,
    build_ticket_created_log_embed,
)

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
    ) -> None:
        """Send a ticket-created log event when a logs channel is available."""

        if logs_channel_id is None:
            return

        try:
            await rest.create_message(
                logs_channel_id,
                embed=build_ticket_created_log_embed(
                    ticket,
                    guild_id=guild_id,
                    locale=locale,
                ),
            )
        except hikari.NotFoundError:
            LOGGER.warning("Configured logs channel %s was not found", logs_channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to write to logs channel %s", logs_channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected ticket-created log for ticket %s", ticket.id)

    async def send_ticket_closed(
        self,
        rest: hikari.api.RESTClient,
        *,
        logs_channel_id: int | None,
        ticket: Ticket,
        guild_id: int,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        """Send a ticket-closed log event when a logs channel is available."""

        if logs_channel_id is None:
            return

        try:
            await rest.create_message(
                logs_channel_id,
                embed=build_ticket_closed_log_embed(
                    ticket,
                    guild_id=guild_id,
                    locale=locale,
                ),
            )
        except hikari.NotFoundError:
            LOGGER.warning("Configured logs channel %s was not found", logs_channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to write to logs channel %s", logs_channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected ticket-closed log for ticket %s", ticket.id)
