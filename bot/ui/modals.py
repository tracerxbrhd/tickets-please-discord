"""Modal definitions for ticket creation and settings updates."""

from __future__ import annotations

import logging

import hikari
import miru

from bot.database.models import Ticket
from bot.i18n import DEFAULT_LOCALE, normalize_locale, t
from bot.ui.embeds import (
    build_channel_names_updated_embed,
    build_panel_error_embed,
    build_settings_panel_embed,
    build_ticket_closed_response_embed,
    build_ticket_closed_thread_embed,
    build_ticket_created_response_embed,
    build_ticket_thread_embed,
)
from bot.utils.formatters import discord_account_name, slugify_channel_name
from bot.utils.permissions import member_permissions, member_role_ids

LOGGER = logging.getLogger(__name__)


def _optional_modal_value(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


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
                locale = (
                    result.validation.settings.locale
                    if result.validation.settings
                    else self._locale
                )
                await runtime.logging_service.send_system_event(
                    runtime.bot.rest,
                    logs_channel_id=result.validation.settings.logs_channel_id
                    if result.validation.settings
                    else None,
                    event_type="user_channel_created",
                    actor_id=int(ctx.user.id),
                    description=t(
                        locale,
                        "logs.user_channel_created_description",
                        channel_id=result.user_channel_id,
                        user_id=int(ctx.user.id),
                    ),
                    locale=locale,
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


class ChannelNamesModal(miru.Modal, title="Channel and category names"):
    """Modal used to rename ticket system channels without recreating them."""

    category_name = miru.TextInput(
        label="Category name",
        placeholder="Leave empty to keep the current category name",
        min_length=0,
        max_length=100,
        required=False,
    )
    support_channel_name = miru.TextInput(
        label="Support channel",
        placeholder="Leave empty to keep the current support channel",
        min_length=0,
        max_length=100,
        required=False,
    )
    logs_channel_name = miru.TextInput(
        label="Logs channel",
        placeholder="Leave empty to keep the current logs channel",
        min_length=0,
        max_length=100,
        required=False,
    )
    settings_channel_name = miru.TextInput(
        label="Settings channel",
        placeholder="Leave empty to keep the current settings channel",
        min_length=0,
        max_length=100,
        required=False,
    )

    def __init__(self, *, guild_id: int, locale: str = DEFAULT_LOCALE) -> None:
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._locale = normalize_locale(locale)
        self.title = t(self._locale, "modals.channel_names_title")
        self.category_name.label = t(self._locale, "modals.category_name")
        self.category_name.placeholder = t(
            self._locale,
            "modals.category_name_placeholder",
        )
        self.support_channel_name.label = t(self._locale, "modals.support_channel_name")
        self.support_channel_name.placeholder = t(
            self._locale,
            "modals.support_channel_name_placeholder",
        )
        self.logs_channel_name.label = t(self._locale, "modals.logs_channel_name")
        self.logs_channel_name.placeholder = t(
            self._locale,
            "modals.logs_channel_name_placeholder",
        )
        self.settings_channel_name.label = t(self._locale, "modals.settings_channel_name")
        self.settings_channel_name.placeholder = t(
            self._locale,
            "modals.settings_channel_name_placeholder",
        )

    async def callback(self, ctx: miru.ModalContext) -> None:
        """Rename configured Discord resources and persist their names."""

        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        permissions = member_permissions(getattr(ctx, "member", None))
        if not permissions & (hikari.Permissions.ADMINISTRATOR | hikari.Permissions.MANAGE_GUILD):
            await ctx.edit_response(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.settings_permission"))
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                settings = await runtime.settings_service.get_settings(
                    session,
                    guild_id=self._guild_id,
                )

            if settings is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.setup_required"))
                )
                return

            locale = settings.locale
            category_name = self._clean_category_name(
                _optional_modal_value(self.category_name.value),
                current=settings.category_name,
            )
            support_name = self._clean_channel_name(
                _optional_modal_value(self.support_channel_name.value),
                current=settings.support_channel_name,
            )
            logs_name = self._clean_channel_name(
                _optional_modal_value(self.logs_channel_name.value),
                current=settings.logs_channel_name,
            )
            settings_name = self._clean_channel_name(
                _optional_modal_value(self.settings_channel_name.value),
                current=settings.settings_channel_name,
            )
            if "" in {category_name, support_name, logs_name, settings_name}:
                await ctx.edit_response(
                    embed=build_panel_error_embed(t(locale, "modals.channel_name_too_short"))
                )
                return

            await self._rename_channel(runtime.bot.rest, settings.category_id, category_name)
            await self._rename_channel(runtime.bot.rest, settings.support_channel_id, support_name)
            await self._rename_channel(runtime.bot.rest, settings.logs_channel_id, logs_name)
            await self._rename_channel(
                runtime.bot.rest,
                settings.settings_channel_id,
                settings_name,
            )

            async with runtime.database.session() as session:
                result = await runtime.settings_service.set_channel_names(
                    session,
                    guild_id=self._guild_id,
                    category_name=category_name,
                    support_channel_name=support_name,
                    logs_channel_name=logs_name,
                    settings_channel_name=settings_name,
                )

            if result is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.setup_required"))
                )
                return

            from bot.ui.views import build_settings_panel_components

            if (
                result.settings.settings_channel_id is not None
                and result.settings.settings_message_id is not None
            ):
                await runtime.bot.rest.edit_message(
                    result.settings.settings_channel_id,
                    result.settings.settings_message_id,
                    embed=build_settings_panel_embed(
                        result.settings,
                        support_roles=result.support_roles,
                    ),
                    components=build_settings_panel_components(result.settings.locale),
                )
            await runtime.logging_service.send_system_event(
                runtime.bot.rest,
                logs_channel_id=result.settings.logs_channel_id,
                event_type="channel_names_updated",
                actor_id=int(ctx.user.id),
                description=t(
                    locale,
                    "settings.channel_names_updated_description",
                    fields=self._format_changed_fields(result.changed_fields, locale=locale),
                ),
                locale=locale,
            )
            await ctx.edit_response(
                embed=build_channel_names_updated_embed(
                    result.changed_fields,
                    locale=result.settings.locale,
                )
            )
        except hikari.ForbiddenError:
            LOGGER.exception("Discord denied channel rename in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "errors.channel_names_update_failed")
                )
            )
        except hikari.BadRequestError:
            LOGGER.exception("Discord rejected channel rename in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "errors.channel_names_update_failed")
                )
            )
        except Exception:
            LOGGER.exception("Unexpected channel rename error in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(self._locale, "errors.channel_names_update_failed")
                )
            )

    def _clean_category_name(self, value: str | None, *, current: str) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()[:100]
        if len(cleaned) < 2:
            return ""
        return cleaned if cleaned != current else None

    def _clean_channel_name(self, value: str | None, *, current: str) -> str | None:
        if value is None:
            return None
        cleaned = slugify_channel_name(value, fallback=current, max_length=100)
        if len(cleaned) < 2:
            return ""
        return cleaned if cleaned != current else None

    async def _rename_channel(
        self,
        rest: hikari.api.RESTClient,
        channel_id: int | None,
        name: str | None,
    ) -> None:
        if channel_id is None or name is None:
            return
        await rest.edit_channel(channel_id, name=name)

    def _format_changed_fields(self, changed_fields: set[str], *, locale: str) -> str:
        if not changed_fields:
            return t(locale, "common.none")
        return ", ".join(t(locale, f"settings.{field}") for field in sorted(changed_fields))


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
