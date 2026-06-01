"""Bot application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import hikari
import lightbulb
import miru

from bot.config import Settings, get_settings
from bot.database.session import Database
from bot.i18n import DEFAULT_LOCALE
from bot.logging import configure_logging
from bot.runtime import Runtime, get_runtime, set_runtime
from bot.services.logging_service import LoggingService
from bot.services.permissions_service import PermissionsService
from bot.services.settings_service import SettingsService
from bot.services.setup_service import SetupService
from bot.services.ticket_service import TicketService
from bot.ui.views import (
    SettingsLanguageSelectView,
    SettingsPanelView,
    SettingsSupportRoleSelectView,
    SupportPanelView,
    TicketThreadView,
)
from bot.utils.permissions import member_permissions, member_role_ids

LOGGER = logging.getLogger(__name__)


def create_bot(settings: Settings | None = None) -> hikari.GatewayBot:
    """Create the Discord bot instance.

    The factory keeps startup testable and gives later stages a single place to attach
    database sessions, miru clients, and persistent views.
    """

    settings = settings or get_settings()
    token = settings.discord_token.get_secret_value()
    database = Database(str(settings.database_url))

    intents = (
        hikari.Intents.GUILDS
        | hikari.Intents.GUILD_MESSAGES
        | hikari.Intents.MESSAGE_CONTENT
    )
    bot = hikari.GatewayBot(token=token, intents=intents)
    miru_client = miru.Client(bot)
    client = lightbulb.client_from_app(
        bot,
        default_enabled_guilds=settings.dev_guild_ids,
        delete_unknown_commands=True,
    )
    set_runtime(
        Runtime(
            bot=bot,
            miru_client=miru_client,
            database=database,
            settings=settings,
            setup_service=SetupService(),
            settings_service=SettingsService(),
            permissions_service=PermissionsService(),
            ticket_service=TicketService(),
            logging_service=LoggingService(),
        )
    )

    @bot.listen(hikari.StartingEvent)
    async def prepare_services(_: hikari.StartingEvent) -> None:
        await client.load_extensions("bot.extensions.tickets_commands")
        await client.load_extensions("bot.extensions.utility_commands")

    @bot.listen(hikari.StartedEvent)
    async def start_command_client(_: hikari.StartedEvent) -> None:
        await client.start()
        miru_client.start_view(SupportPanelView(), bind_to=None)
        miru_client.start_view(SettingsPanelView(), bind_to=None)
        miru_client.start_view(SettingsSupportRoleSelectView(), bind_to=None)
        miru_client.start_view(SettingsLanguageSelectView(), bind_to=None)
        miru_client.start_view(TicketThreadView(), bind_to=None)
        LOGGER.info("Lightbulb command client started")

    @bot.listen(hikari.GuildMessageCreateEvent)
    async def mirror_claimed_ticket_message(event: hikari.GuildMessageCreateEvent) -> None:
        message = event.message
        author = getattr(message, "author", None)
        if author is None or getattr(author, "is_bot", False):
            return

        raw_content = getattr(message, "content", "") or ""
        content = "" if raw_content is hikari.UNDEFINED else str(raw_content)
        raw_attachments = getattr(message, "attachments", ()) or ()
        if raw_attachments is hikari.UNDEFINED:
            raw_attachments = ()
        attachments = list(raw_attachments)
        if not content.strip() and not attachments:
            return

        guild_id = int(event.guild_id)
        author_id = int(author.id)
        thread_id = int(message.channel_id)
        try:
            async with database.session() as session:
                context = await get_runtime().ticket_service.get_message_log_context(
                    session,
                    guild_id=guild_id,
                    thread_id=thread_id,
                    author_id=author_id,
                    author_role_ids=member_role_ids(event.member),
                    author_permissions=member_permissions(event.member),
                )
            if context is None:
                return

            locale = context.settings.locale if context.settings else DEFAULT_LOCALE
            await get_runtime().logging_service.send_ticket_message(
                bot.rest,
                ticket=context.ticket,
                guild_id=guild_id,
                author_id=author_id,
                author_name=getattr(author, "username", ""),
                author_avatar_url=_user_avatar_url(author),
                is_moderator=context.is_moderator,
                content=content,
                attachment_names=_attachment_names(attachments),
                message_id=int(message.id),
                created_at=getattr(message, "created_at", None) or datetime.now(UTC),
                locale=locale,
            )
        except Exception:
            LOGGER.exception("Failed to mirror ticket message in guild %s", guild_id)

    @bot.listen(hikari.StoppingEvent)
    async def stop_services(_: hikari.StoppingEvent) -> None:
        LOGGER.info("Stopping Lightbulb command client")
        await client.stop()
        miru_client.clear()
        LOGGER.info("Closing database connections")
        await database.dispose()

    return bot


def _user_avatar_url(user: object) -> str | None:
    for attribute_name in ("display_avatar_url", "avatar_url", "default_avatar_url"):
        value = getattr(user, attribute_name, None)
        if value is not None and value is not hikari.UNDEFINED:
            return str(value)
    return None


def _attachment_names(attachments: list[object]) -> list[str]:
    names: list[str] = []
    for attachment in attachments:
        filename = str(getattr(attachment, "filename", "attachment"))
        url = getattr(attachment, "url", None)
        names.append(f"[{filename}]({url})" if url else filename)
    return names


async def wait_for_dependencies(settings: Settings) -> None:
    """Wait for external services before opening the Discord gateway."""

    database = Database(str(settings.database_url))
    try:
        LOGGER.info("Checking database connection")
        await database.wait_until_ready()
        LOGGER.info("Database connection is available")
    finally:
        await database.dispose()


def main() -> None:
    """Run the bot process."""

    settings = get_settings()
    configure_logging(settings.log_level)

    LOGGER.info("Starting Tickets! Please bot in %s environment", settings.environment)
    asyncio.run(wait_for_dependencies(settings))
    bot = create_bot(settings)
    bot.run()


if __name__ == "__main__":
    main()
