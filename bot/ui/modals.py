"""Modal definitions for ticket creation and settings updates."""

from __future__ import annotations

import logging

import hikari
import miru

from bot.database.models import Ticket
from bot.i18n import DEFAULT_LOCALE, normalize_locale, t
from bot.ui.embeds import (
    build_panel_error_embed,
    build_ticket_closed_response_embed,
    build_ticket_closed_thread_embed,
    build_ticket_created_response_embed,
    build_ticket_thread_embed,
)
from bot.utils.formatters import discord_account_name
from bot.utils.permissions import member_permissions, member_role_ids

LOGGER = logging.getLogger(__name__)


class TicketCreateModal(miru.Modal, title="Create ticket"):
    """Modal used to collect the initial ticket title and description."""

    subject = miru.TextInput(
        label="Ticket subject",
        placeholder="Briefly describe the topic",
        min_length=3,
        max_length=120,
        required=True,
    )
    description = miru.TextInput(
        label="Problem description",
        placeholder="Describe the problem and what you have already tried",
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=10,
        max_length=1500,
        required=True,
    )

    def __init__(
        self,
        *,
        guild_id: int,
        panel_channel_id: int,
        panel_message_id: int,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._panel_channel_id = panel_channel_id
        self._panel_message_id = panel_message_id
        self._locale = normalize_locale(locale)
        self.title = t(self._locale, "modals.create_title")
        self.subject.label = t(self._locale, "modals.ticket_subject")
        self.subject.placeholder = t(self._locale, "modals.ticket_subject_placeholder")
        self.description.label = t(self._locale, "modals.problem_description")
        self.description.placeholder = t(
            self._locale,
            "modals.problem_description_placeholder",
        )

    async def callback(self, ctx: miru.ModalContext) -> None:
        """Create the ticket after the user submits the modal."""

        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        title = str(self.subject.value or "").strip()
        description = str(self.description.value or "").strip()
        if len(title) < 3 or len(description) < 10:
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.too_short")
                )
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                result = await runtime.ticket_service.create_ticket(
                    session,
                    runtime.bot.rest,
                    guild_id=self._guild_id,
                    panel_channel_id=self._panel_channel_id,
                    panel_message_id=self._panel_message_id,
                    user_id=int(ctx.user.id),
                    user_name=discord_account_name(ctx.user),
                    title=title,
                    description=description,
                )

            if not result.validation.is_valid or result.ticket is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        result.validation.reason or t(self._locale, "modals.create_failed")
                    )
                )
                return

            from bot.ui.views import build_ticket_thread_components

            try:
                locale = (
                    result.validation.settings.locale
                    if result.validation.settings
                    else self._locale
                )
                ticket_embed = build_ticket_thread_embed(result.ticket, locale=locale)
                ticket_components = build_ticket_thread_components(locale)

                mentions = [f"<@{result.ticket.user_id}>"]
                mentions.extend(f"<@&{role_id}>" for role_id in result.support_role_ids)
                await runtime.bot.rest.create_message(
                    result.ticket.thread_id,
                    content=" ".join(mentions),
                    embed=ticket_embed,
                    components=ticket_components,
                    user_mentions=[result.ticket.user_id],
                    role_mentions=result.support_role_ids,
                )
            except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
                LOGGER.exception(
                    "Failed to send first ticket message for ticket %s",
                    result.ticket.id,
                )
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        t(self._locale, "modals.thread_message_failed")
                    )
                )
                return

            log_thread_id = await runtime.logging_service.send_ticket_created(
                runtime.bot.rest,
                logs_channel_id=result.validation.settings.logs_channel_id
                if result.validation.settings
                else None,
                ticket=result.ticket,
                guild_id=self._guild_id,
                locale=result.validation.settings.locale
                if result.validation.settings
                else self._locale,
            )
            if log_thread_id is not None:
                async with runtime.database.session() as session:
                    updated_ticket = await runtime.ticket_service.set_ticket_log_thread(
                        session,
                        ticket_id=result.ticket.id,
                        log_thread_id=log_thread_id,
                    )
                if updated_ticket is not None:
                    result.ticket.log_thread_id = updated_ticket.log_thread_id

            if result.user_channel_created:
                await runtime.logging_service.send_system_event(
                    runtime.bot.rest,
                    logs_channel_id=result.validation.settings.logs_channel_id
                    if result.validation.settings
                    else None,
                    event_type="user_channel_created",
                    actor_id=int(ctx.user.id),
                    description=(
                        "Created private ticket channel "
                        f"<#{result.user_channel_id}> for <@{ctx.user.id}>."
                    ),
                )
            await ctx.edit_response(
                embed=build_ticket_created_response_embed(
                    result.ticket,
                    guild_id=self._guild_id,
                    locale=result.validation.settings.locale
                    if result.validation.settings
                    else self._locale,
                )
            )
        except hikari.ForbiddenError:
            LOGGER.exception("Discord denied ticket creation in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.create_forbidden")
                )
            )
        except hikari.BadRequestError:
            LOGGER.exception("Discord rejected ticket creation in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.create_rejected")
                )
            )
        except Exception:
            LOGGER.exception("Unexpected ticket creation error in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.create_unexpected")
                )
            )


class TicketCloseConfirmModal(miru.Modal, title="Close ticket"):
    """Modal used to collect the close reason for irreversible ticket closure."""

    reason = miru.TextInput(
        label="Close reason",
        placeholder="Describe why this ticket is being closed",
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=3,
        max_length=1000,
        required=True,
    )

    def __init__(
        self,
        *,
        guild_id: int,
        thread_id: int,
        ticket_message_id: int,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        super().__init__(timeout=120)
        self._guild_id = guild_id
        self._thread_id = thread_id
        self._ticket_message_id = ticket_message_id
        self._locale = normalize_locale(locale)
        self.title = t(self._locale, "modals.close_title")
        self.reason.label = t(self._locale, "modals.close_reason")
        self.reason.placeholder = t(self._locale, "modals.close_reason_placeholder")

    async def callback(self, ctx: miru.ModalContext) -> None:
        """Close a ticket after explicit user confirmation."""

        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        close_reason = str(self.reason.value or "").strip()
        if len(close_reason) < 3:
            await ctx.edit_response(
                embed=build_panel_error_embed(t(self._locale, "modals.close_reason_required"))
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        member = getattr(ctx, "member", None)
        try:
            async with runtime.database.session() as session:
                result = await runtime.ticket_service.close_ticket(
                    session,
                    guild_id=self._guild_id,
                    thread_id=self._thread_id,
                    actor_id=int(ctx.user.id),
                    actor_role_ids=member_role_ids(member),
                    actor_permissions=member_permissions(member),
                    close_reason=close_reason,
                )

            if not result.validation.is_valid or result.ticket is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        result.validation.reason or t(self._locale, "modals.close_failed")
                    )
                )
                return

            await self._remove_close_button(runtime.bot.rest, result.ticket)
            locale = (
                result.validation.settings.locale
                if result.validation.settings
                else self._locale
            )
            await self._send_closed_thread_message(runtime.bot.rest, result.ticket, locale=locale)
            archived = await self._archive_thread(runtime.bot.rest, result.ticket.thread_id)

            await runtime.logging_service.send_ticket_closed(
                runtime.bot.rest,
                logs_channel_id=result.validation.settings.logs_channel_id
                if result.validation.settings
                else None,
                ticket=result.ticket,
                guild_id=self._guild_id,
                locale=locale,
            )
            await ctx.edit_response(
                embed=build_ticket_closed_response_embed(
                    result.ticket,
                    archived=archived,
                    locale=locale,
                )
            )
        except hikari.ForbiddenError:
            LOGGER.exception("Discord denied ticket closure in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.close_forbidden")
                )
            )
        except hikari.BadRequestError:
            LOGGER.exception("Discord rejected ticket closure in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.close_rejected")
                )
            )
        except Exception:
            LOGGER.exception("Unexpected ticket closure error in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "modals.close_unexpected")
                )
            )

    async def _remove_close_button(
        self,
        rest: hikari.api.RESTClient,
        ticket: Ticket,
    ) -> None:
        try:
            await rest.edit_message(
                self._thread_id,
                self._ticket_message_id,
                components=[],
            )
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to remove close button for ticket %s", ticket.id)

    async def _send_closed_thread_message(
        self,
        rest: hikari.api.RESTClient,
        ticket: Ticket,
        *,
        locale: str,
    ) -> None:
        try:
            await rest.create_message(
                ticket.thread_id,
                embed=build_ticket_closed_thread_embed(ticket, locale=locale),
            )
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to send closed message for ticket %s", ticket.id)

    async def _archive_thread(self, rest: hikari.api.RESTClient, thread_id: int) -> bool:
        try:
            await rest.edit_channel(thread_id, archived=True, locked=True)
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to archive ticket thread %s", thread_id)
            return False
        return True
