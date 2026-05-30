"""Bot application entrypoint."""

from __future__ import annotations

import logging

import hikari
import lightbulb
import miru

from bot.config import Settings, get_settings
from bot.database.session import Database
from bot.logging import configure_logging
from bot.runtime import Runtime, set_runtime
from bot.services.logging_service import LoggingService
from bot.services.permissions_service import PermissionsService
from bot.services.settings_service import SettingsService
from bot.services.setup_service import SetupService
from bot.services.ticket_service import TicketService
from bot.ui.views import SettingsPanelView, SupportPanelView, TicketThreadView

LOGGER = logging.getLogger(__name__)


def create_bot(settings: Settings | None = None) -> hikari.GatewayBot:
    """Create the Discord bot instance.

    The factory keeps startup testable and gives later stages a single place to attach
    database sessions, miru clients, and persistent views.
    """

    settings = settings or get_settings()
    token = settings.discord_token.get_secret_value()
    database = Database(str(settings.database_url))

    intents = hikari.Intents.GUILDS | hikari.Intents.GUILD_MESSAGES
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
        LOGGER.info("Checking database connection")
        await database.check_connection()
        LOGGER.info("Database connection is available")
        await client.load_extensions("bot.extensions.tickets_commands")

    @bot.listen(hikari.StartedEvent)
    async def start_command_client(_: hikari.StartedEvent) -> None:
        await client.start()
        miru_client.start_view(SupportPanelView(), bind_to=None)
        miru_client.start_view(SettingsPanelView(), bind_to=None)
        miru_client.start_view(TicketThreadView(), bind_to=None)
        LOGGER.info("Lightbulb command client started")

    @bot.listen(hikari.StoppingEvent)
    async def stop_services(_: hikari.StoppingEvent) -> None:
        LOGGER.info("Stopping Lightbulb command client")
        await client.stop()
        miru_client.clear()
        LOGGER.info("Closing database connections")
        await database.dispose()

    return bot


def main() -> None:
    """Run the bot process."""

    settings = get_settings()
    configure_logging(settings.log_level)

    LOGGER.info("Starting Tickets! Please bot in %s environment", settings.environment)
    bot = create_bot(settings)
    bot.run()


if __name__ == "__main__":
    main()
