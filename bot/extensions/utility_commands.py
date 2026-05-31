"""General utility slash commands."""

from __future__ import annotations

import logging

import hikari
import lightbulb

from bot.i18n import DEFAULT_LOCALE
from bot.runtime import get_runtime
from bot.ui.embeds import build_ping_embed

LOGGER = logging.getLogger(__name__)
loader = lightbulb.Loader()


async def _respond_ephemeral(
    ctx: lightbulb.Context,
    *,
    embed: hikari.Embed,
) -> None:
    await ctx.respond(
        embed=embed,
        flags=hikari.MessageFlag.EPHEMERAL,
    )


def _gateway_latency_ms(bot: hikari.GatewayBot) -> int | None:
    latency = getattr(bot, "heartbeat_latency", None)
    if latency is None:
        latencies = getattr(bot, "heartbeat_latencies", None)
        if isinstance(latencies, dict) and latencies:
            latency = max(latencies.values())

    if latency is None or latency is hikari.UNDEFINED:
        return None

    try:
        return max(0, round(float(latency) * 1000))
    except (TypeError, ValueError):
        return None


@loader.command
class Ping(
    lightbulb.SlashCommand,
    name="ping",
    description="Check current bot latency.",
):
    """Return a compact health check for the bot process."""

    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        runtime = get_runtime()
        locale = DEFAULT_LOCALE
        if ctx.guild_id is not None:
            try:
                async with runtime.database.session() as session:
                    settings = await runtime.settings_service.get_settings(
                        session,
                        guild_id=int(ctx.guild_id),
                    )
                if settings is not None:
                    locale = settings.locale
            except Exception:
                LOGGER.exception("Failed to load locale for ping in guild %s", ctx.guild_id)

        await _respond_ephemeral(
            ctx,
            embed=build_ping_embed(
                latency_ms=_gateway_latency_ms(runtime.bot),
                locale=locale,
            ),
        )
