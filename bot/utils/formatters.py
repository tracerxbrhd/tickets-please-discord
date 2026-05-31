"""Formatting helpers for channels, tickets, timestamps, and mentions."""

from __future__ import annotations

import re
from datetime import datetime


def channel_mention(channel_id: int | None, *, fallback: str = "not configured") -> str:
    """Return a Discord channel mention or a placeholder."""

    if channel_id is None:
        return fallback
    return f"<#{channel_id}>"


def message_jump_url(guild_id: int, channel_id: int, message_id: int) -> str:
    """Build a Discord message jump URL."""

    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def channel_jump_url(guild_id: int, channel_id: int) -> str:
    """Build a Discord channel or thread jump URL."""

    return f"https://discord.com/channels/{guild_id}/{channel_id}"


def discord_timestamp(value: datetime | None, *, fallback: str = "not available") -> str:
    """Format a datetime for Discord markdown."""

    if value is None:
        return fallback
    return f"<t:{int(value.timestamp())}:f>"


def slugify_channel_name(value: str, *, fallback: str = "ticket", max_length: int = 80) -> str:
    """Return a conservative Discord channel/thread name fragment."""

    normalized = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9а-яё]+", "-", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    normalized = normalized[:max_length].strip("-")
    return normalized or fallback


def discord_account_name(user: object) -> str | None:
    """Return the Discord account username, not server nickname or display name."""

    value = getattr(user, "username", None)
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def user_ticket_channel_name(account_name: str | None, *, user_id: int) -> str:
    """Build the current per-user ticket channel name."""

    account_slug = slugify_channel_name(
        account_name or "",
        fallback=f"user-{user_id}",
        max_length=70,
    )
    return f"ticket-{account_slug}"


def ticket_thread_name(ticket_number: int, title: str) -> str:
    """Build a per-ticket thread name."""

    title_slug = slugify_channel_name(title, fallback="request", max_length=50)
    return f"ticket-{ticket_number}-{title_slug}"


def ticket_log_thread_name(ticket_number: int, title: str) -> str:
    """Build a logs-channel thread name for one ticket."""

    title_slug = slugify_channel_name(title, fallback="log", max_length=45)
    return f"ticket-{ticket_number}-log-{title_slug}"
