"""Domain exceptions used by services and Discord adapters."""

from __future__ import annotations


class TicketsPleaseError(Exception):
    """Base class for expected application errors."""


class GuildOnlyCommandError(TicketsPleaseError):
    """Raised when a guild-only command is used outside a guild."""


class MissingUserPermissionsError(TicketsPleaseError):
    """Raised when a user does not have enough permissions for an action."""


class MissingBotPermissionsError(TicketsPleaseError):
    """Raised when the bot cannot perform an action in the guild."""
