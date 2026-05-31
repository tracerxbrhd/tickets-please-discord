"""Embed builders for support panels, tickets, logs, and settings."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import hikari

from bot.database.models import GuildSettings, SupportRole, Ticket
from bot.i18n import DEFAULT_LOCALE, available_languages, normalize_locale, t
from bot.utils.formatters import (
    channel_jump_url,
    channel_mention,
    discord_timestamp,
    message_jump_url,
)
from bot.utils.limits import MAX_OPEN_TICKETS_PER_USER

if TYPE_CHECKING:
    from bot.services.setup_service import SetupResult

BRAND_COLOR = hikari.Color.of(0x5865F2)
SUCCESS_COLOR = hikari.Color.of(0x2ECC71)
WARNING_COLOR = hikari.Color.of(0xF1C40F)


def build_support_panel_embed(locale: str = DEFAULT_LOCALE) -> hikari.Embed:
    """Build the public support panel embed."""

    locale = normalize_locale(locale)
    return (
        hikari.Embed(
            title="Tickets! Please",
            description=t(locale, "support_panel.description"),
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(
            t(locale, "support_panel.create_title"),
            t(locale, "support_panel.create_body"),
            inline=True,
        )
        .add_field(
            t(locale, "support_panel.my_title"),
            t(locale, "support_panel.my_body"),
            inline=True,
        )
        .set_footer("Tickets! Please")
    )


def build_settings_panel_embed(
    settings: GuildSettings,
    *,
    support_roles: list[SupportRole],
) -> hikari.Embed:
    """Build the settings channel embed for the current guild configuration."""

    locale = normalize_locale(settings.locale)
    return (
        hikari.Embed(
            title=t(locale, "settings.title"),
            description=t(locale, "settings.description"),
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(
            t(locale, "settings.category"),
            channel_mention(settings.category_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.support_channel"),
            channel_mention(settings.support_channel_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.logs_channel"),
            channel_mention(settings.logs_channel_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.settings_channel"),
            channel_mention(settings.settings_channel_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.system"),
            t(locale, "common.enabled" if settings.is_enabled else "common.disabled"),
            inline=True,
        )
        .add_field(
            t(locale, "settings.support_roles"),
            _format_support_roles(support_roles, locale=locale),
            inline=True,
        )
        .add_field(t(locale, "settings.language"), _format_language(settings.locale), inline=True)
        .add_field(
            t(locale, "settings.open_ticket_limit"),
            t(locale, "settings.open_ticket_limit_value", limit=MAX_OPEN_TICKETS_PER_USER),
            inline=True,
        )
        .add_field(
            t(locale, "settings.attachment_mode"),
            t(locale, "settings.attachment_mode_value"),
            inline=True,
        )
        .add_field(t(locale, "settings.channel_format"), "ticket-{account-name}", inline=True)
        .add_field(t(locale, "settings.thread_format"), "ticket-{number}", inline=True)
    )


def build_support_role_updated_embed(role_id: int, *, locale: str = DEFAULT_LOCALE) -> hikari.Embed:
    """Build an ephemeral settings update response."""

    locale = normalize_locale(locale)
    return hikari.Embed(
        title=t(locale, "settings.support_role_updated_title"),
        description=t(locale, "settings.support_role_updated_description", role_id=role_id),
        color=SUCCESS_COLOR,
        timestamp=datetime.now(UTC),
    )


def build_language_updated_embed(locale: str) -> hikari.Embed:
    """Build an ephemeral language update response."""

    locale = normalize_locale(locale)
    return hikari.Embed(
        title=t(locale, "settings.language_updated_title"),
        description=t(
            locale,
            "settings.language_updated_description",
            language=_format_language(locale),
        ),
        color=SUCCESS_COLOR,
        timestamp=datetime.now(UTC),
    )


def build_setup_summary_embed(result: SetupResult) -> hikari.Embed:
    """Build an ephemeral command response describing setup changes."""

    locale = normalize_locale(result.locale)
    support_message_url = message_jump_url(
        result.guild_id,
        result.support_channel_id,
        result.support_message_id,
    )
    settings_message_url = message_jump_url(
        result.guild_id,
        result.settings_channel_id,
        result.settings_message_id,
    )
    created = "\n".join(f"- {item}" for item in result.created_resources) or t(
        locale,
        "common.none",
    )
    reused = "\n".join(f"- {item}" for item in result.reused_resources) or t(
        locale,
        "common.none",
    )

    return (
        hikari.Embed(
            title=t(locale, "setup.title"),
            description=t(locale, "setup.description"),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "setup.category"), channel_mention(result.category_id), inline=True)
        .add_field(
            t(locale, "setup.support"),
            channel_mention(result.support_channel_id),
            inline=True,
        )
        .add_field(t(locale, "setup.logs"), channel_mention(result.logs_channel_id), inline=True)
        .add_field(
            t(locale, "setup.settings"),
            channel_mention(result.settings_channel_id),
            inline=True,
        )
        .add_field(t(locale, "setup.created"), created, inline=False)
        .add_field(t(locale, "setup.reused"), reused, inline=False)
        .add_field(t(locale, "setup.support_panel"), support_message_url, inline=False)
        .add_field(t(locale, "setup.settings_panel"), settings_message_url, inline=False)
    )


def build_status_embed(settings: GuildSettings | None) -> hikari.Embed:
    """Build status command response."""

    if settings is None:
        return hikari.Embed(
            title=t(DEFAULT_LOCALE, "status.title"),
            description=t(DEFAULT_LOCALE, "status.not_configured"),
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )

    locale = normalize_locale(settings.locale)
    return (
        hikari.Embed(
            title=t(locale, "status.title"),
            description=t(locale, "status.description"),
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(
            t(locale, "settings.system"),
            t(locale, "common.enabled" if settings.is_enabled else "common.disabled"),
            inline=True,
        )
        .add_field(
            t(locale, "settings.category"),
            channel_mention(settings.category_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.support_channel"),
            channel_mention(settings.support_channel_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.logs_channel"),
            channel_mention(settings.logs_channel_id),
            inline=True,
        )
        .add_field(
            t(locale, "settings.settings_channel"),
            channel_mention(settings.settings_channel_id),
            inline=True,
        )
        .add_field(t(locale, "settings.language"), _format_language(settings.locale), inline=True)
        .add_field(t(locale, "status.created"), discord_timestamp(settings.created_at), inline=True)
        .add_field(t(locale, "status.updated"), discord_timestamp(settings.updated_at), inline=True)
    )


def build_reset_embed(was_configured: bool, *, locale: str = DEFAULT_LOCALE) -> hikari.Embed:
    """Build reset command response."""

    locale = normalize_locale(locale)
    description = (
        t(locale, "reset.done")
        if was_configured
        else t(locale, "reset.empty")
    )
    return hikari.Embed(
        title=t(locale, "reset.title"),
        description=description,
        color=WARNING_COLOR,
        timestamp=datetime.now(UTC),
    )


def build_log_embed(
    *,
    event_type: str,
    actor_id: int,
    description: str,
) -> hikari.Embed:
    """Build a log channel embed."""

    return (
        hikari.Embed(
            title=f"Ticket system event: {event_type}",
            description=description,
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("User", f"<@{actor_id}>", inline=True)
        .add_field("Event", event_type, inline=True)
    )


def build_panel_error_embed(reason: str) -> hikari.Embed:
    """Build an ephemeral error response for support panel actions."""

    return hikari.Embed(
        title="Tickets! Please",
        description=reason,
        color=WARNING_COLOR,
        timestamp=datetime.now(UTC),
    )


def build_ticket_thread_embed(ticket: Ticket, *, locale: str = DEFAULT_LOCALE) -> hikari.Embed:
    """Build the first message inside a ticket thread."""

    locale = normalize_locale(locale)
    return (
        hikari.Embed(
            title=t(
                locale,
                "ticket.thread_title",
                number=ticket.ticket_number,
                title=ticket.title,
            ),
            description=ticket.description,
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "ticket.status"), f"`{ticket.status.value}`", inline=True)
        .add_field(t(locale, "ticket.author"), f"<@{ticket.user_id}>", inline=True)
        .add_field(
            t(locale, "ticket.files"),
            t(locale, "ticket.files_hint"),
            inline=False,
        )
        .set_footer("Tickets! Please")
    )


def build_ticket_closed_thread_embed(
    ticket: Ticket,
    *,
    locale: str = DEFAULT_LOCALE,
) -> hikari.Embed:
    """Build the final message posted into a closed ticket thread."""

    locale = normalize_locale(locale)
    return (
        hikari.Embed(
            title=t(locale, "ticket.closed_thread_title", number=ticket.ticket_number),
            description=t(locale, "ticket.closed_thread_description"),
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "ticket.subject"), ticket.title, inline=False)
        .add_field(t(locale, "ticket.closed_by"), f"<@{ticket.closed_by_id}>", inline=True)
        .add_field(t(locale, "ticket.closed_at"), discord_timestamp(ticket.closed_at), inline=True)
        .set_footer("Tickets! Please")
    )


def build_ticket_created_response_embed(
    ticket: Ticket,
    *,
    guild_id: int,
    locale: str = DEFAULT_LOCALE,
) -> hikari.Embed:
    """Build the ephemeral response after a ticket is created."""

    locale = normalize_locale(locale)
    thread_url = channel_jump_url(guild_id, ticket.thread_id)
    return (
        hikari.Embed(
            title=t(locale, "ticket.created_title"),
            description=t(
                locale,
                "ticket.created_description",
                number=ticket.ticket_number,
                url=thread_url,
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "ticket.subject"), ticket.title, inline=False)
        .add_field(t(locale, "ticket.status"), f"`{ticket.status.value}`", inline=True)
    )


def build_ticket_closed_response_embed(
    ticket: Ticket,
    *,
    archived: bool,
    locale: str = DEFAULT_LOCALE,
) -> hikari.Embed:
    """Build the ephemeral response after a ticket is closed."""

    locale = normalize_locale(locale)
    archive_note = (
        t(locale, "ticket.archive_ok")
        if archived
        else t(locale, "ticket.archive_failed")
    )
    return (
        hikari.Embed(
            title=t(locale, "ticket.closed_title"),
            description=t(
                locale,
                "ticket.closed_response",
                number=ticket.ticket_number,
                archive_note=archive_note,
            ),
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "ticket.subject"), ticket.title, inline=False)
        .add_field(t(locale, "ticket.status"), f"`{ticket.status.value}`", inline=True)
    )


def build_ticket_created_log_embed(
    ticket: Ticket,
    *,
    guild_id: int,
    locale: str = DEFAULT_LOCALE,
) -> hikari.Embed:
    """Build a logs-channel embed for a created ticket."""

    locale = normalize_locale(locale)
    thread_url = channel_jump_url(guild_id, ticket.thread_id)
    return (
        hikari.Embed(
            title=t(locale, "logs.ticket_created_title"),
            description=t(
                locale,
                "logs.ticket_created_description",
                number=ticket.ticket_number,
                url=thread_url,
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "logs.user"), f"<@{ticket.user_id}>", inline=True)
        .add_field(t(locale, "logs.ticket_id"), str(ticket.id), inline=True)
        .add_field(t(locale, "ticket.status"), f"`{ticket.status.value}`", inline=True)
        .add_field(t(locale, "logs.title"), ticket.title, inline=False)
    )


def build_ticket_closed_log_embed(
    ticket: Ticket,
    *,
    guild_id: int,
    locale: str = DEFAULT_LOCALE,
) -> hikari.Embed:
    """Build a logs-channel embed for a closed ticket."""

    locale = normalize_locale(locale)
    thread_url = channel_jump_url(guild_id, ticket.thread_id)
    return (
        hikari.Embed(
            title=t(locale, "logs.ticket_closed_title"),
            description=t(
                locale,
                "logs.ticket_closed_description",
                number=ticket.ticket_number,
                url=thread_url,
            ),
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field(t(locale, "logs.user"), f"<@{ticket.user_id}>", inline=True)
        .add_field(t(locale, "logs.moderator"), f"<@{ticket.closed_by_id}>", inline=True)
        .add_field(t(locale, "logs.ticket_id"), str(ticket.id), inline=True)
        .add_field(t(locale, "ticket.closed_at"), discord_timestamp(ticket.closed_at), inline=True)
        .add_field(t(locale, "logs.title"), ticket.title, inline=False)
    )


def build_user_tickets_embed(
    *,
    open_tickets: list[Ticket],
    closed_tickets: list[Ticket],
    guild_id: int,
    locale: str = DEFAULT_LOCALE,
) -> hikari.Embed:
    """Build a compact ephemeral list of a user's tickets."""

    locale = normalize_locale(locale)
    embed = hikari.Embed(
        title=t(locale, "my_tickets.title"),
        description=t(locale, "my_tickets.description"),
        color=BRAND_COLOR,
        timestamp=datetime.now(UTC),
    )

    if not open_tickets and not closed_tickets:
        embed.description = t(locale, "my_tickets.empty")
        return embed

    def format_ticket(ticket: Ticket, *, include_closed_at: bool) -> str:
        thread_url = channel_jump_url(guild_id, ticket.thread_id)
        created_at = discord_timestamp(ticket.created_at)
        title = _trim_embed_text(ticket.title, limit=60)
        lines = [
            f"`#{ticket.ticket_number}` [{title}]({thread_url})",
            f"{t(locale, 'my_tickets.status')}: `{ticket.status.value}`",
            f"{t(locale, 'my_tickets.created')}: {created_at}",
        ]
        if include_closed_at and ticket.closed_at is not None:
            lines.append(
                f"{t(locale, 'my_tickets.closed')}: {discord_timestamp(ticket.closed_at)}"
            )
        return "\n".join(lines)

    embed.add_field(
        t(locale, "my_tickets.open"),
        _ticket_list_field(
            open_tickets,
            formatter=lambda ticket: format_ticket(ticket, include_closed_at=False),
            empty_text=t(locale, "my_tickets.open_empty"),
            max_items=5,
            locale=locale,
        ),
        inline=False,
    )
    embed.add_field(
        t(locale, "my_tickets.recently_closed"),
        _ticket_list_field(
            closed_tickets,
            formatter=lambda ticket: format_ticket(ticket, include_closed_at=True),
            empty_text=t(locale, "my_tickets.closed_empty"),
            max_items=5,
            locale=locale,
        ),
        inline=False,
    )

    return embed


def _ticket_list_field(
    tickets: list[Ticket],
    *,
    formatter: Callable[[Ticket], str],
    empty_text: str,
    max_items: int,
    locale: str,
) -> str:
    if not tickets:
        return empty_text

    visible_tickets = tickets[:max_items]
    items = [formatter(ticket) for ticket in visible_tickets]
    hidden_count = len(tickets) - len(visible_tickets)
    if hidden_count > 0:
        items.append(t(locale, "my_tickets.more", count=hidden_count))
    return "\n\n".join(items)


def _trim_embed_text(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}..."


def _format_support_roles(
    support_roles: list[SupportRole],
    *,
    locale: str = DEFAULT_LOCALE,
) -> str:
    if not support_roles:
        return t(locale, "common.not_configured")
    return ", ".join(f"<@&{role.role_id}>" for role in support_roles)


def _format_language(locale: str) -> str:
    locale = normalize_locale(locale)
    for language in available_languages():
        if language.code == locale:
            return f"{language.native_name} (`{language.code}`)"
    return locale
