"""Persistent component views for support and ticket interactions."""

from __future__ import annotations

import logging

import hikari
import miru

from bot.ui.embeds import (
    build_panel_error_embed,
    build_settings_panel_embed,
    build_support_role_updated_embed,
    build_user_tickets_embed,
)
from bot.ui.modals import TicketCloseConfirmModal, TicketCreateModal
from bot.ui.selects import SETTINGS_SUPPORT_ROLE_SELECT_CUSTOM_ID
from bot.utils.permissions import member_permissions, member_role_ids

LOGGER = logging.getLogger(__name__)

SUPPORT_CREATE_TICKET_CUSTOM_ID = "tickets_please:support:create_ticket"
SUPPORT_MY_TICKETS_CUSTOM_ID = "tickets_please:support:my_tickets"
TICKET_CLOSE_CUSTOM_ID = "tickets_please:ticket:close"


def build_support_panel_components() -> list[hikari.api.ComponentBuilder]:
    """Build component rows for the public support panel message."""

    return SupportPanelView().build()


def build_ticket_thread_components() -> list[hikari.api.ComponentBuilder]:
    """Build component rows for the first ticket thread message."""

    return TicketThreadView().build()


def build_settings_panel_components() -> list[hikari.api.ComponentBuilder]:
    """Build component rows for the settings panel message."""

    return SettingsPanelView().build()


class SupportPanelView(miru.View):
    """Unbound persistent view for all support panel messages."""

    def __init__(self) -> None:
        super().__init__(timeout=None, autodefer=False)

    async def _panel_ids(self, ctx: miru.ViewContext) -> tuple[int, int, int] | None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed("This panel only works in a server."),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        message = ctx.message
        if message is None:
            await ctx.respond(
                embed=build_panel_error_embed("Could not identify the panel message."),
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
                await ctx.respond(
                    embed=build_panel_error_embed(prompt.validation.reason or "Panel unavailable."),
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            await ctx.respond_with_modal(
                TicketCreateModal(
                    guild_id=guild_id,
                    panel_channel_id=channel_id,
                    panel_message_id=message_id,
                )
            )
        except Exception:
            LOGGER.exception("Failed to handle create-ticket button in guild %s", guild_id)
            await ctx.respond(
                embed=build_panel_error_embed(
                    "Could not process this button. Details were written to bot logs."
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
                        ticket_list.validation.reason or "Panel unavailable."
                    ),
                )
                return

            await ctx.edit_response(
                embed=build_user_tickets_embed(
                    open_tickets=ticket_list.open_tickets,
                    closed_tickets=ticket_list.closed_tickets,
                    guild_id=guild_id,
                ),
            )
        except Exception:
            LOGGER.exception("Failed to handle my-tickets button in guild %s", guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Could not get your ticket list. Details were written to bot logs."
                ),
            )


class SettingsPanelView(miru.View):
    """Unbound persistent view for ticket settings controls."""

    def __init__(self) -> None:
        super().__init__(timeout=None, autodefer=False)

    async def _settings_ids(self, ctx: miru.ViewContext) -> tuple[int, int, int] | None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed("This panel only works in a server."),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        if ctx.message is None:
            await ctx.respond(
                embed=build_panel_error_embed("Could not identify the settings message."),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        return int(guild_id), int(ctx.channel_id), int(ctx.message.id)

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
        settings_ids = await self._settings_ids(ctx)
        if settings_ids is None:
            return

        guild_id, channel_id, message_id = settings_ids
        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        selected_role = select.values[0] if select.values else None
        if selected_role is None:
            await ctx.edit_response(
                embed=build_panel_error_embed("Select one support role.")
            )
            return

        role_id = int(getattr(selected_role, "id", selected_role))
        if role_id == guild_id:
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "`@everyone` cannot be selected as the support role."
                )
            )
            return

        permissions = member_permissions(getattr(ctx, "member", None))
        if not permissions & (hikari.Permissions.ADMINISTRATOR | hikari.Permissions.MANAGE_GUILD):
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "You do not have permission to change ticket settings."
                )
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
                    await ctx.edit_response(
                        embed=build_panel_error_embed(
                            "The ticket system is not configured yet. Run `/tickets-setup`."
                        )
                    )
                    return

                if (
                    settings.settings_channel_id != channel_id
                    or settings.settings_message_id != message_id
                ):
                    await ctx.edit_response(
                        embed=build_panel_error_embed(
                            "This settings panel is stale. Use the current message."
                        )
                    )
                    return

                result = await runtime.settings_service.set_support_role(
                    session,
                    guild_id=guild_id,
                    role_id=role_id,
                )
                await runtime.permissions_service.apply_support_roles(
                    session,
                    runtime.bot.rest,
                    guild_id=guild_id,
                    settings=settings,
                    old_role_ids=result.old_role_ids,
                    new_role_ids=result.new_role_ids,
                )

            await runtime.bot.rest.edit_message(
                channel_id,
                message_id,
                embed=build_settings_panel_embed(
                    settings,
                    support_roles=result.support_roles,
                ),
                components=build_settings_panel_components(),
            )
            await runtime.logging_service.send_system_event(
                runtime.bot.rest,
                logs_channel_id=settings.logs_channel_id,
                event_type="support_role_assigned",
                actor_id=int(ctx.user.id),
                description=f"Support role changed to <@&{role_id}>.",
            )
            await ctx.edit_response(embed=build_support_role_updated_embed(role_id))
        except Exception:
            LOGGER.exception("Failed to update support role in guild %s", guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Could not update the support role. Details were written to bot logs."
                )
            )


class TicketThreadView(miru.View):
    """Unbound persistent view for ticket thread controls."""

    def __init__(self) -> None:
        super().__init__(timeout=None, autodefer=False)

    async def _thread_ids(self, ctx: miru.ViewContext) -> tuple[int, int, int] | None:
        guild_id = ctx.guild_id
        if guild_id is None:
            await ctx.respond(
                embed=build_panel_error_embed("This button only works in a server."),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        if ctx.message is None:
            await ctx.respond(
                embed=build_panel_error_embed("Could not identify the ticket message."),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return None

        return int(guild_id), int(ctx.channel_id), int(ctx.message.id)

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
                    embed=build_panel_error_embed(validation.reason or "Ticket unavailable."),
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            await ctx.respond_with_modal(
                TicketCloseConfirmModal(
                    guild_id=guild_id,
                    thread_id=thread_id,
                    ticket_message_id=ticket_message_id,
                )
            )
        except Exception:
            LOGGER.exception("Failed to handle close-ticket button in guild %s", guild_id)
            await ctx.respond(
                embed=build_panel_error_embed(
                    "Could not process ticket closure. Details were written to bot logs."
                ),
                flags=hikari.MessageFlag.EPHEMERAL,
            )
