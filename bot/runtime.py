"""Runtime dependency container for Discord extensions."""

from __future__ import annotations

from dataclasses import dataclass

import hikari
import miru

from bot.config import Settings
from bot.database.session import Database
from bot.services.logging_service import LoggingService
from bot.services.permissions_service import PermissionsService
from bot.services.settings_service import SettingsService
from bot.services.setup_service import SetupService
from bot.services.ticket_service import TicketService


@dataclass(slots=True)
class Runtime:
    """Dependencies shared by Lightbulb extensions."""

    bot: hikari.GatewayBot
    miru_client: miru.Client
    database: Database
    settings: Settings
    setup_service: SetupService
    settings_service: SettingsService
    permissions_service: PermissionsService
    ticket_service: TicketService
    logging_service: LoggingService


_runtime: Runtime | None = None


def set_runtime(runtime: Runtime) -> None:
    """Store process runtime dependencies."""

    global _runtime
    _runtime = runtime


def get_runtime() -> Runtime:
    """Return configured runtime dependencies."""

    if _runtime is None:
        raise RuntimeError("Runtime has not been configured")
    return _runtime
