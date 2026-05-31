"""Persistent component views for support and ticket interactions."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import cast

import hikari
import miru

from bot.i18n import DEFAULT_LOCALE, available_languages, normalize_locale, t
from bot.ui.embeds import (
    build_language_updated_embed,
    build_panel_error_embed,
    build_settings_control_embed,
    build_settings_panel_embed,
    build_support_panel_embed,
    build_support_role_updated_embed,
    build_ticket_claimed_response_embed,
    build_ticket_thread_embed,
    build_user_tickets_embed,
)
from bot.ui.modals import TicketCloseConfirmModal, TicketCreateModal
from bot.ui.selects import (
    SETTINGS_LANGUAGE_BUTTON_CUSTOM_ID,
    SETTINGS_LANGUAGE_SELECT_CUSTOM_ID,
    SETTINGS_SUPPORT_ROLE_BUTTON_CUSTOM_ID,
    SETTINGS_SUPPORT_ROLE_SELECT_CUSTOM_ID,
)
from bot.utils.permissions import member_permissions, member_role_ids

LOGGER = logging.getLogger(__name__)

SUPPORT_CREATE_TICKET_CUSTOM_ID = "tickets_please:support:create_ticket"
SUPPORT_MY_TICKETS_CUSTOM_ID = "tickets_please:support:my_tickets"
TICKET_CLAIM_CUSTOM_ID = "tickets_please:ticket:claim"
TICKET_CLOSE_CUSTOM_ID = "tickets_please:ticket:close"


def build_support_panel_components(
    locale: str = DEFAULT_LOCALE,
) -> Sequence[hikari.api.ComponentBuilder]:
    """Build component rows for the public support panel message."""
    return SupportPanelView(locale).build()


def build_ticket_thread_components(
    locale: str = DEFAULT_LOCALE,
) -> Sequence[hikari.api.ComponentBuilder]:
    """Build component rows for the first ticket thread message."""
    return TicketThreadView(locale).build()


def build_settings_panel_components(
    locale: str = DEFAULT_LOCALE,
) -> Sequence[hikari.api.ComponentBuilder]:
    """Build component rows for the settings panel message."""
    return SettingsPanelView(locale).build()


def build_settings_support_role_select_components(
    locale: str = DEFAULT_LOCALE,
) -> Sequence[hikari.api.ComponentBuilder]:
    """Build component rows for the support-role settings prompt."""
    return SettingsSupportRoleSelectView(locale).build()


def build_settings_language_select_components(
    locale: str = DEFAULT_LOCALE,
) -> Sequence[hikari.api.ComponentBuilder]:
    """Build component rows for the language settings prompt."""
    return SettingsLanguageSelectView(locale).build()


def _language_options() -> list[miru.SelectOption]:
    return [
        miru.SelectOption(
            label=language.native_name,
            value=language.code,
            description=language.name,
        )
        for language in available_languages()
    ]


class SupportPanelView(miru.View):
    """Unbound persistent view for all support panel messages."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        super().__init__(timeout=None, autodefer=False)
        locale = normalize_locale(locale)
        for item in self.children:
            if getattr(item, "custom_id", None) == SUPPORT_CREATE_TICKET_CUSTOM_ID:
                button = cast(miru.Button, item)
                button.label = t(locale, "buttons.create_ticket")
            elif getattr(item, "custom_id", None) == SUPPORT_MY_TICKETS_CUSTOM_ID:
                button = cast(miru.Button, item)
                button.label = t(locale, "buttons.my_tickets")

    async def _panel_ids(self, ctx: miru.ViewContext) -> tuple[int, int, int] | None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.server_only")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        message = ctx.message
        if message is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.panel_message_missing")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        return int(guild_id), int(ctx.channel_id), int(message.id)

    @miru.button(
        label="Create ticket",
        style=hikari.ButtonStyle.PRIMARY,
        custom_id=SUPPORT_CREATE_TICKET_CUSTOM_ID,
    )
    async def create_ticket(
        self,
        ctx: miru.ViewContext,
        button: miru.Button,
    ) -> None:
        del button

        panel_ids = await self._panel_ids(ctx)
        if panel_ids is None:
            return

        guild_id, channel_id, message_id = panel_ids

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                prompt = await runtime.ticket_service.prepare_ticket_creation(
                    session,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    message_id=message_id,
                    user_id=int(ctx.user.id),
                )

            if not prompt.validation.is_valid:
                locale = (
                    prompt.validation.settings.locale
                    if prompt.validation.settings
                    else DEFAULT_LOCALE
                )
                await ctx.respond(
                    embed=build_panel_error_embed(
                        prompt.validation.reason or t(locale, "errors.panel_unavailable")
                    ),
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            await ctx.respond_with_modal(
                TicketCreateModal(
                    guild_id=guild_id,
                    panel_channel_id=channel_id,
                    panel_message_id=message_id,
                    locale=prompt.validation.settings.locale
                    if prompt.validation.settings
                    else DEFAULT_LOCALE,
                )
            )
        except Exception:
            LOGGER.exception("Failed to handle create-ticket button in guild %s", guild_id)
            await ctx.respond(
                embed=build_panel_error_embed(
                    t(DEFAULT_LOCALE, "errors.button_failed")
                ),
                flags=hikari.MessageFlag.EPHEMERAL,
            )

    @miru.button(
        label="My tickets",
        style=hikari.ButtonStyle.SECONDARY,
        custom_id=SUPPORT_MY_TICKETS_CUSTOM_ID,
    )
    async def my_tickets(
        self,
        ctx: miru.ViewContext,
        button: miru.Button,
    ) -> None:
        del button

        panel_ids = await self._panel_ids(ctx)
        if panel_ids is None:
            return

        guild_id, channel_id, message_id = panel_ids
        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                ticket_list = await runtime.ticket_service.list_user_tickets(
                    session,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    message_id=message_id,
                    user_id=int(ctx.user.id),
                )

            if not ticket_list.validation.is_valid:
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        ticket_list.validation.reason
                        or t(DEFAULT_LOCALE, "errors.panel_unavailable")
                    ),
                )
                return

            await ctx.edit_response(
                embed=build_user_tickets_embed(
                    open_tickets=ticket_list.open_tickets,
                    closed_tickets=ticket_list.closed_tickets,
                    guild_id=guild_id,
                    locale=ticket_list.validation.settings.locale
                    if ticket_list.validation.settings
                    else DEFAULT_LOCALE,
                ),
            )
        except Exception:
            LOGGER.exception("Failed to handle my-tickets button in guild %s", guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(DEFAULT_LOCALE, "errors.ticket_list_failed")
                ),
            )


class SettingsPanelView(miru.View):
    """Unbound persistent view for the settings summary message."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        super().__init__(timeout=None, autodefer=False)
        locale = normalize_locale(locale)
        for item in self.children:
            custom_id = getattr(item, "custom_id", None)
            if custom_id == SETTINGS_SUPPORT_ROLE_BUTTON_CUSTOM_ID:
                button = cast(miru.Button, item)
                button.label = t(locale, "buttons.change_support_role")
            elif custom_id == SETTINGS_LANGUAGE_BUTTON_CUSTOM_ID:
                button = cast(miru.Button, item)
                button.label = t(locale, "buttons.change_language")

    async def _settings_ids(self, ctx: miru.ViewContext) -> tuple[int, int, int] | None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.server_only")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        if ctx.message is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.settings_message_missing")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        return int(guild_id), int(ctx.channel_id), int(ctx.message.id)

    async def _open_settings_control(
        self,
        ctx: miru.ViewContext,
        *,
        control: str,
    ) -> None:
        settings_ids = await self._settings_ids(ctx)
        if settings_ids is None:
            return

        guild_id, channel_id, message_id = settings_ids
        permissions = member_permissions(getattr(ctx, "member", None))
        if not permissions & (hikari.Permissions.ADMINISTRATOR | hikari.Permissions.MANAGE_GUILD):
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.settings_permission")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                settings = await runtime.settings_service.get_settings(
                    session,
                    guild_id=guild_id,
                )

            if settings is None:
                await ctx.respond(
                    embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.setup_required")),
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            locale = settings.locale
            if (
                settings.settings_channel_id != channel_id
                or settings.settings_message_id != message_id
            ):
                await ctx.respond(
                    embed=build_panel_error_embed(t(locale, "errors.settings_stale")),
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            await ctx.respond(
                embed=build_settings_control_embed(
                    title=t(locale, f"settings.{control}_prompt_title"),
                    description=t(locale, f"settings.{control}_prompt_description"),
                    locale=locale,
                ),
                components=(
                    build_settings_support_role_select_components(locale)
                    if control == "support_role"
                    else build_settings_language_select_components(locale)
                ),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
        except Exception:
            LOGGER.exception("Failed to open settings control in guild %s", guild_id)
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.settings_control_failed")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )

    @miru.button(
        label="Support role",
        style=hikari.ButtonStyle.SECONDARY,
        custom_id=SETTINGS_SUPPORT_ROLE_BUTTON_CUSTOM_ID,
    )
    async def open_support_role_select(
        self,
        ctx: miru.ViewContext,
        button: miru.Button,
    ) -> None:
        del button
        await self._open_settings_control(
            ctx,
            control="support_role",
        )

    @miru.button(
        label="Language",
        style=hikari.ButtonStyle.SECONDARY,
        custom_id=SETTINGS_LANGUAGE_BUTTON_CUSTOM_ID,
    )
    async def open_language_select(
        self,
        ctx: miru.ViewContext,
        button: miru.Button,
    ) -> None:
        del button
        await self._open_settings_control(
            ctx,
            control="language",
        )


class SettingsSupportRoleSelectView(miru.View):
    """Persistent view for ephemeral support-role settings prompts."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        super().__init__(timeout=None, autodefer=False)
        locale = normalize_locale(locale)
        for item in self.children:
            if getattr(item, "custom_id", None) == SETTINGS_SUPPORT_ROLE_SELECT_CUSTOM_ID:
                role_select = cast(miru.RoleSelect, item)
                role_select.placeholder = t(locale, "selects.support_role")

    @miru.role_select(
        placeholder="Select support role",
        min_values=1,
        max_values=1,
        custom_id=SETTINGS_SUPPORT_ROLE_SELECT_CUSTOM_ID,
    )
    async def support_role_select(
        self,
        ctx: miru.ViewContext,
        select: miru.RoleSelect,
    ) -> None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.server_only")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return
        guild_id_int = int(guild_id)

        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        selected_role = select.values[0] if select.values else None
        if selected_role is None:
            await ctx.edit_response(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.role_required"))
            )
            return

        role_id = int(getattr(selected_role, "id", selected_role))
        if role_id == guild_id_int:
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(DEFAULT_LOCALE, "errors.everyone_role")
                )
            )
            return

        permissions = member_permissions(getattr(ctx, "member", None))
        if not permissions & (hikari.Permissions.ADMINISTRATOR | hikari.Permissions.MANAGE_GUILD):
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(DEFAULT_LOCALE, "errors.settings_permission")
                )
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                settings = await runtime.settings_service.get_settings(
                    session,
                    guild_id=guild_id_int,
                )
                if settings is None:
                    await ctx.edit_response(
                        embed=build_panel_error_embed(
                            t(DEFAULT_LOCALE, "errors.setup_required")
                        )
                    )
                    return
                locale = settings.locale

                result = await runtime.settings_service.set_support_role(
                    session,
                    guild_id=guild_id_int,
                    role_id=role_id,
                )
                await runtime.permissions_service.apply_support_roles(
                    session,
                    runtime.bot.rest,
                    guild_id=guild_id_int,
                    settings=settings,
                    old_role_ids=result.old_role_ids,
                    new_role_ids=result.new_role_ids,
                )

            if settings.settings_channel_id is None or settings.settings_message_id is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(t(locale, "errors.settings_message_missing"))
                )
                return

            await runtime.bot.rest.edit_message(
                settings.settings_channel_id,
                settings.settings_message_id,
                embed=build_settings_panel_embed(
                    settings,
                    support_roles=result.support_roles,
                ),
                components=build_settings_panel_components(settings.locale),
            )
            await runtime.logging_service.send_system_event(
                runtime.bot.rest,
                logs_channel_id=settings.logs_channel_id,
                event_type="support_role_assigned",
                actor_id=int(ctx.user.id),
                description=f"Support role changed to <@&{role_id}>.",
            )
            await ctx.edit_response(
                embed=build_support_role_updated_embed(role_id, locale=settings.locale)
            )
        except Exception:
            LOGGER.exception("Failed to update support role in guild %s", guild_id_int)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    t(DEFAULT_LOCALE, "errors.support_role_update_failed")
                )
            )


class SettingsLanguageSelectView(miru.View):
    """Persistent view for ephemeral language settings prompts."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        super().__init__(timeout=None, autodefer=False)
        locale = normalize_locale(locale)
        for item in self.children:
            if getattr(item, "custom_id", None) == SETTINGS_LANGUAGE_SELECT_CUSTOM_ID:
                text_select = cast(miru.TextSelect, item)
                text_select.placeholder = t(locale, "selects.language")

    @miru.text_select(
        placeholder="Select language",
        min_values=1,
        max_values=1,
        options=_language_options(),
        custom_id=SETTINGS_LANGUAGE_SELECT_CUSTOM_ID,
    )
    async def language_select(
        self,
        ctx: miru.ViewContext,
        select: miru.TextSelect,
    ) -> None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.server_only")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return
        guild_id_int = int(guild_id)

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

        selected_locale = normalize_locale(select.values[0] if select.values else None)

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                settings = await runtime.settings_service.get_settings(
                    session,
                    guild_id=guild_id_int,
                )
                if settings is None:
                    await ctx.edit_response(
                        embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.setup_required"))
                    )
                    return

                result = await runtime.settings_service.set_locale(
                    session,
                    guild_id=guild_id_int,
                    locale=selected_locale,
                )
                if result is None:
                    await ctx.edit_response(
                        embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.setup_required"))
                    )
                    return

            if (
                result.settings.settings_channel_id is None
                or result.settings.settings_message_id is None
            ):
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        t(result.new_locale, "errors.settings_message_missing")
                    )
                )
                return

            await runtime.bot.rest.edit_message(
                result.settings.settings_channel_id,
                result.settings.settings_message_id,
                embed=build_settings_panel_embed(
                    result.settings,
                    support_roles=result.support_roles,
                ),
                components=build_settings_panel_components(result.new_locale),
            )
            await self._refresh_support_panel(runtime.bot.rest, result.settings)
            await runtime.logging_service.send_system_event(
                runtime.bot.rest,
                logs_channel_id=result.settings.logs_channel_id,
                event_type="language_updated",
                actor_id=int(ctx.user.id),
                description=f"Ticket system language changed to `{result.new_locale}`.",
            )
            await ctx.edit_response(embed=build_language_updated_embed(result.new_locale))
        except Exception:
            LOGGER.exception("Failed to update language in guild %s", guild_id_int)
            await ctx.edit_response(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.language_update_failed"))
            )

    async def _refresh_support_panel(
        self,
        rest: hikari.api.RESTClient,
        settings: object,
    ) -> None:
        support_channel_id = getattr(settings, "support_channel_id", None)
        support_message_id = getattr(settings, "support_message_id", None)
        locale = getattr(settings, "locale", DEFAULT_LOCALE)
        if support_channel_id is None or support_message_id is None:
            return

        try:
            await rest.edit_message(
                support_channel_id,
                support_message_id,
                embed=build_support_panel_embed(locale),
                components=build_support_panel_components(locale),
            )
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to refresh localized support panel")


class TicketThreadView(miru.View):
    """Unbound persistent view for ticket thread controls."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        super().__init__(timeout=None, autodefer=False)
        locale = normalize_locale(locale)
        for item in self.children:
            if getattr(item, "custom_id", None) == TICKET_CLAIM_CUSTOM_ID:
                button = cast(miru.Button, item)
                button.label = t(locale, "buttons.claim_ticket")
            elif getattr(item, "custom_id", None) == TICKET_CLOSE_CUSTOM_ID:
                button = cast(miru.Button, item)
                button.label = t(locale, "buttons.close_ticket")

    async def _thread_ids(self, ctx: miru.ViewContext) -> tuple[int, int, int] | None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.server_only")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        if ctx.message is None:
            await ctx.respond(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.ticket_message_missing")),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        return int(guild_id), int(ctx.channel_id), int(ctx.message.id)

    @miru.button(
        label="Take ticket",
        style=hikari.ButtonStyle.SUCCESS,
        custom_id=TICKET_CLAIM_CUSTOM_ID,
    )
    async def claim_ticket(
        self,
        ctx: miru.ViewContext,
        button: miru.Button,
    ) -> None:
        del button

        thread_ids = await self._thread_ids(ctx)
        if thread_ids is None:
            return

        guild_id, thread_id, ticket_message_id = thread_ids
        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        from bot.runtime import get_runtime

        runtime = get_runtime()
        member = getattr(ctx, "member", None)
        try:
            async with runtime.database.session() as session:
                result = await runtime.ticket_service.claim_ticket(
                    session,
                    guild_id=guild_id,
                    thread_id=thread_id,
                    actor_id=int(ctx.user.id),
                    actor_role_ids=member_role_ids(member),
                    actor_permissions=member_permissions(member),
                )

            if not result.validation.is_valid or result.ticket is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        result.validation.reason or t(DEFAULT_LOCALE, "errors.ticket_unavailable")
                    ),
                )
                return

            locale = (
                result.validation.settings.locale
                if result.validation.settings
                else DEFAULT_LOCALE
            )
            await runtime.bot.rest.edit_message(
                thread_id,
                ticket_message_id,
                embed=build_ticket_thread_embed(result.ticket, locale=locale),
                components=build_ticket_thread_components(locale),
            )
            await runtime.logging_service.send_ticket_claimed(
                runtime.bot.rest,
                logs_channel_id=result.validation.settings.logs_channel_id
                if result.validation.settings
                else None,
                ticket=result.ticket,
                locale=locale,
            )
            await ctx.edit_response(
                embed=build_ticket_claimed_response_embed(result.ticket, locale=locale),
            )
        except Exception:
            LOGGER.exception("Failed to handle claim-ticket button in guild %s", guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(t(DEFAULT_LOCALE, "errors.claim_failed")),
            )

    @miru.button(
        label="Close ticket",
        style=hikari.ButtonStyle.DANGER,
        custom_id=TICKET_CLOSE_CUSTOM_ID,
    )
    async def close_ticket(
        self,
        ctx: miru.ViewContext,
        button: miru.Button,
    ) -> None:
        del button

        thread_ids = await self._thread_ids(ctx)
        if thread_ids is None:
            return

        guild_id, thread_id, ticket_message_id = thread_ids

        from bot.runtime import get_runtime

        runtime = get_runtime()
        member = getattr(ctx, "member", None)
        try:
            async with runtime.database.session() as session:
                validation = await runtime.ticket_service.validate_ticket_close(
                    session,
                    guild_id=guild_id,
                    thread_id=thread_id,
                    actor_id=int(ctx.user.id),
                    actor_role_ids=member_role_ids(member),
                    actor_permissions=member_permissions(member),
                )

            if not validation.is_valid:
                await ctx.respond(
                    embed=build_panel_error_embed(
                        validation.reason or t(DEFAULT_LOCALE, "errors.ticket_unavailable")
                    ),
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            await ctx.respond_with_modal(
                TicketCloseConfirmModal(
                    guild_id=guild_id,
                    thread_id=thread_id,
                    ticket_message_id=ticket_message_id,
                    locale=validation.settings.locale
                    if validation.settings
                    else DEFAULT_LOCALE,
                )
            )
        except Exception:
            LOGGER.exception("Failed to handle close-ticket button in guild %s", guild_id)
            await ctx.respond(
                embed=build_panel_error_embed(
                    t(DEFAULT_LOCALE, "errors.close_failed")
                ),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
