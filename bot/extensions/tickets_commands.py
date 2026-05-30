"""Slash commands for the ticket system setup stage."""

from __future__ import annotations

import logging

import hikari
import lightbulb

from bot.runtime import get_runtime
from bot.ui.embeds import build_reset_embed, build_setup_summary_embed, build_status_embed
from bot.utils.permissions import (
    SETUP_BOT_PERMISSIONS,
    SETUP_USER_PERMISSIONS,
    format_permissions,
    missing_permissions,
)

LOGGER = logging.getLogger(__name__)
loader = lightbulb.Loader()


async def _respond_ephemeral(
    ctx: lightbulb.Context,
    *,
    content: str | None = None,
    embed: hikari.Embed | None = None,
) -> None:
    kwargs: dict[str, object] = {"flags": hikari.MessageFlag.EPHEMERAL}
    if content is not None:
        kwargs["content"] = content
    if embed is not None:
        kwargs["embed"] = embed
    await ctx.respond(**kwargs)


async def _defer_ephemeral(ctx: lightbulb.Context) -> None:
    await ctx.defer(ephemeral=True)


async def _get_allowed_guild_id(ctx: lightbulb.Context) -> int | None:
    guild_id = ctx.guild_id
    if guild_id is None:
        await _respond_ephemeral(ctx, content="Эта команда доступна только на сервере.")
        return None

    member = ctx.member
    user_permissions = getattr(member, "permissions", hikari.Permissions.NONE)
    if user_permissions is hikari.UNDEFINED or user_permissions is None:
        user_permissions = hikari.Permissions.NONE
    user_missing = missing_permissions(user_permissions, SETUP_USER_PERMISSIONS)
    if user_missing != hikari.Permissions.NONE:
        await _respond_ephemeral(
            ctx,
            content=(
                "Недостаточно прав для управления тикет-системой. "
                f"Не хватает: {format_permissions(user_missing)}."
            ),
        )
        return None

    app_permissions = ctx.interaction.app_permissions
    if app_permissions is hikari.UNDEFINED or app_permissions is None:
        app_permissions = hikari.Permissions.NONE
    bot_missing = missing_permissions(app_permissions, SETUP_BOT_PERMISSIONS)
    if bot_missing != hikari.Permissions.NONE:
        await _respond_ephemeral(
            ctx,
            content=(
                "Боту не хватает прав для настройки каналов. "
                f"Не хватает: {format_permissions(bot_missing)}."
            ),
        )
        return None

    return int(guild_id)


@loader.command
class TicketsSetup(
    lightbulb.SlashCommand,
    name="tickets-setup",
    description="Create or update the Tickets! Please channel structure.",
):
    """Create the base channel structure and persist IDs in the database."""

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        guild_id = await _get_allowed_guild_id(ctx)
        if guild_id is None:
            return

        await _defer_ephemeral(ctx)
        runtime = get_runtime()

        try:
            async with runtime.database.session() as session:
                result = await runtime.setup_service.setup_guild(
                    session,
                    runtime.bot.rest,
                    guild_id=guild_id,
                )

            await runtime.logging_service.send_system_event(
                runtime.bot.rest,
                logs_channel_id=result.logs_channel_id,
                event_type="setup_completed",
                actor_id=int(ctx.user.id),
                description="Tickets! Please system channels were created or updated.",
            )
            await _respond_ephemeral(ctx, embed=build_setup_summary_embed(result))
        except hikari.ForbiddenError:
            LOGGER.exception("Discord denied setup action in guild %s", guild_id)
            await _respond_ephemeral(
                ctx,
                content=(
                    "Discord отклонил действие из-за прав доступа. "
                    "Проверьте роль бота и разрешения на управление каналами."
                ),
            )
        except hikari.BadRequestError:
            LOGGER.exception("Discord rejected setup payload in guild %s", guild_id)
            await _respond_ephemeral(
                ctx,
                content="Discord отклонил запрос настройки. Подробности записаны в логи бота.",
            )
        except Exception:
            LOGGER.exception("Unexpected setup error in guild %s", guild_id)
            await _respond_ephemeral(
                ctx,
                content="Не удалось выполнить настройку. Подробности записаны в логи бота.",
            )


@loader.command
class TicketsStatus(
    lightbulb.SlashCommand,
    name="tickets-status",
    description="Show saved Tickets! Please configuration for this server.",
):
    """Show current saved setup state."""

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        guild_id = await _get_allowed_guild_id(ctx)
        if guild_id is None:
            return

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                settings = await runtime.settings_service.get_settings(session, guild_id=guild_id)
            await _respond_ephemeral(ctx, embed=build_status_embed(settings))
        except Exception:
            LOGGER.exception("Unexpected status error in guild %s", guild_id)
            await _respond_ephemeral(
                ctx,
                content="Не удалось получить статус. Подробности записаны в логи бота.",
            )


@loader.command
class TicketsReset(
    lightbulb.SlashCommand,
    name="tickets-reset",
    description="Forget saved Tickets! Please configuration without deleting channels.",
):
    """Forget saved setup state without deleting Discord resources."""

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        guild_id = await _get_allowed_guild_id(ctx)
        if guild_id is None:
            return

        await _defer_ephemeral(ctx)
        runtime = get_runtime()

        try:
            async with runtime.database.session() as session:
                result = await runtime.settings_service.reset_settings(
                    session,
                    guild_id=guild_id,
                )

            await runtime.logging_service.send_system_event(
                runtime.bot.rest,
                logs_channel_id=result.logs_channel_id,
                event_type="settings_reset",
                actor_id=int(ctx.user.id),
                description=(
                    "Tickets! Please saved configuration was reset. "
                    "Discord channels were not deleted."
                ),
            )
            await _respond_ephemeral(ctx, embed=build_reset_embed(result.was_configured))
        except Exception:
            LOGGER.exception("Unexpected reset error in guild %s", guild_id)
            await _respond_ephemeral(
                ctx,
                content="Не удалось сбросить настройки. Подробности записаны в логи бота.",
            )
