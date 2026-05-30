"""Embed builders for support panels, tickets, logs, and settings."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import hikari

from bot.database.models import GuildSettings, SupportRole, Ticket
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


def build_support_panel_embed() -> hikari.Embed:
    """Build the public support panel embed."""

    return (
        hikari.Embed(
            title="Tickets! Please",
            description=(
                "Создайте обращение в поддержку или посмотрите список своих обращений."
            ),
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Создать обращение", "Открывает форму нового обращения.", inline=True)
        .add_field("Мои обращения", "Показывает ваши последние обращения.", inline=True)
        .set_footer("Tickets! Please")
    )


def build_settings_panel_embed(
    settings: GuildSettings,
    *,
    support_roles: list[SupportRole],
) -> hikari.Embed:
    """Build the settings channel embed for the current guild configuration."""

    return (
        hikari.Embed(
            title="Tickets! Please settings",
            description="Базовая конфигурация тикет-системы для этого сервера.",
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Категория", channel_mention(settings.category_id), inline=True)
        .add_field("Канал поддержки", channel_mention(settings.support_channel_id), inline=True)
        .add_field("Канал логов", channel_mention(settings.logs_channel_id), inline=True)
        .add_field("Канал настроек", channel_mention(settings.settings_channel_id), inline=True)
        .add_field("Система", "enabled" if settings.is_enabled else "disabled", inline=True)
        .add_field("Роли поддержки", _format_support_roles(support_roles), inline=True)
        .add_field(
            "Лимит открытых тикетов",
            f"{MAX_OPEN_TICKETS_PER_USER} на пользователя",
            inline=True,
        )
        .add_field("Режим вложений", "fallback: attach in ticket thread", inline=True)
        .add_field("Формат каналов", "ticket-{user}", inline=True)
        .add_field("Формат веток", "ticket-{number}", inline=True)
    )


def build_support_role_updated_embed(role_id: int) -> hikari.Embed:
    """Build an ephemeral settings update response."""

    return hikari.Embed(
        title="Роль поддержки обновлена",
        description=f"Новая роль поддержки: <@&{role_id}>.",
        color=SUCCESS_COLOR,
        timestamp=datetime.now(UTC),
    )


def build_setup_summary_embed(result: SetupResult) -> hikari.Embed:
    """Build an ephemeral command response describing setup changes."""

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
    created = "\n".join(f"- {item}" for item in result.created_resources) or "none"
    reused = "\n".join(f"- {item}" for item in result.reused_resources) or "none"

    return (
        hikari.Embed(
            title="Tickets! Please setup complete",
            description="Базовая структура каналов создана или обновлена.",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Категория", channel_mention(result.category_id), inline=True)
        .add_field("Поддержка", channel_mention(result.support_channel_id), inline=True)
        .add_field("Логи", channel_mention(result.logs_channel_id), inline=True)
        .add_field("Настройки", channel_mention(result.settings_channel_id), inline=True)
        .add_field("Создано", created, inline=False)
        .add_field("Переиспользовано", reused, inline=False)
        .add_field("Панель поддержки", support_message_url, inline=False)
        .add_field("Панель настроек", settings_message_url, inline=False)
    )


def build_status_embed(settings: GuildSettings | None) -> hikari.Embed:
    """Build status command response."""

    if settings is None:
        return hikari.Embed(
            title="Tickets! Please status",
            description="Тикет-система еще не настроена. Запустите `/tickets-setup`.",
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )

    return (
        hikari.Embed(
            title="Tickets! Please status",
            description="Текущая сохраненная конфигурация сервера.",
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Система", "enabled" if settings.is_enabled else "disabled", inline=True)
        .add_field("Категория", channel_mention(settings.category_id), inline=True)
        .add_field("Канал поддержки", channel_mention(settings.support_channel_id), inline=True)
        .add_field("Канал логов", channel_mention(settings.logs_channel_id), inline=True)
        .add_field("Канал настроек", channel_mention(settings.settings_channel_id), inline=True)
        .add_field("Создано", discord_timestamp(settings.created_at), inline=True)
        .add_field("Обновлено", discord_timestamp(settings.updated_at), inline=True)
    )


def build_reset_embed(was_configured: bool) -> hikari.Embed:
    """Build reset command response."""

    description = (
        "Сохраненная конфигурация удалена. Каналы Discord не удалялись."
        if was_configured
        else "Сохраненной конфигурации не было."
    )
    return hikari.Embed(
        title="Tickets! Please reset",
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


def build_ticket_thread_embed(ticket: Ticket) -> hikari.Embed:
    """Build the first message inside a ticket thread."""

    return (
        hikari.Embed(
            title=f"Обращение #{ticket.ticket_number}: {ticket.title}",
            description=ticket.description,
            color=BRAND_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Статус", f"`{ticket.status.value}`", inline=True)
        .add_field("Автор", f"<@{ticket.user_id}>", inline=True)
        .add_field(
            "Файлы",
            "Если нужно, прикрепите файл следующим сообщением в этой ветке.",
            inline=False,
        )
        .set_footer("Tickets! Please")
    )


def build_ticket_closed_thread_embed(ticket: Ticket) -> hikari.Embed:
    """Build the final message posted into a closed ticket thread."""

    return (
        hikari.Embed(
            title=f"Обращение #{ticket.ticket_number} закрыто",
            description=(
                "Это обращение закрыто. Если нужна помощь по новой проблеме, "
                "создайте новое обращение."
            ),
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Тема", ticket.title, inline=False)
        .add_field("Закрыл", f"<@{ticket.closed_by_id}>", inline=True)
        .add_field("Дата закрытия", discord_timestamp(ticket.closed_at), inline=True)
        .set_footer("Tickets! Please")
    )


def build_ticket_created_response_embed(ticket: Ticket, *, guild_id: int) -> hikari.Embed:
    """Build the ephemeral response after a ticket is created."""

    thread_url = channel_jump_url(guild_id, ticket.thread_id)
    return (
        hikari.Embed(
            title="Обращение создано",
            description=f"Ваше обращение `#{ticket.ticket_number}` создано: {thread_url}",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Тема", ticket.title, inline=False)
        .add_field("Статус", f"`{ticket.status.value}`", inline=True)
    )


def build_ticket_closed_response_embed(ticket: Ticket, *, archived: bool) -> hikari.Embed:
    """Build the ephemeral response after a ticket is closed."""

    archive_note = (
        "Ветка архивирована."
        if archived
        else "Ветка закрыта в БД, но архивировать ее не удалось."
    )
    return (
        hikari.Embed(
            title="Обращение закрыто",
            description=f"Обращение `#{ticket.ticket_number}` закрыто. {archive_note}",
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("Тема", ticket.title, inline=False)
        .add_field("Статус", f"`{ticket.status.value}`", inline=True)
    )


def build_ticket_created_log_embed(ticket: Ticket, *, guild_id: int) -> hikari.Embed:
    """Build a logs-channel embed for a created ticket."""

    thread_url = channel_jump_url(guild_id, ticket.thread_id)
    return (
        hikari.Embed(
            title="Ticket system event: ticket_created",
            description=f"Создано обращение `#{ticket.ticket_number}`: {thread_url}",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("User", f"<@{ticket.user_id}>", inline=True)
        .add_field("Ticket ID", str(ticket.id), inline=True)
        .add_field("Status", f"`{ticket.status.value}`", inline=True)
        .add_field("Title", ticket.title, inline=False)
    )


def build_ticket_closed_log_embed(ticket: Ticket, *, guild_id: int) -> hikari.Embed:
    """Build a logs-channel embed for a closed ticket."""

    thread_url = channel_jump_url(guild_id, ticket.thread_id)
    return (
        hikari.Embed(
            title="Ticket system event: ticket_closed",
            description=f"Закрыто обращение `#{ticket.ticket_number}`: {thread_url}",
            color=WARNING_COLOR,
            timestamp=datetime.now(UTC),
        )
        .add_field("User", f"<@{ticket.user_id}>", inline=True)
        .add_field("Moderator", f"<@{ticket.closed_by_id}>", inline=True)
        .add_field("Ticket ID", str(ticket.id), inline=True)
        .add_field("Closed at", discord_timestamp(ticket.closed_at), inline=True)
        .add_field("Title", ticket.title, inline=False)
    )


def build_user_tickets_embed(
    *,
    open_tickets: list[Ticket],
    closed_tickets: list[Ticket],
    guild_id: int,
) -> hikari.Embed:
    """Build a compact ephemeral list of a user's tickets."""

    embed = hikari.Embed(
        title="Мои обращения",
        description="Открытые обращения и последние закрытые обращения.",
        color=BRAND_COLOR,
        timestamp=datetime.now(UTC),
    )

    if not open_tickets and not closed_tickets:
        embed.description = "У вас пока нет обращений."
        return embed

    def format_ticket(ticket: Ticket, *, include_closed_at: bool) -> str:
        thread_url = channel_jump_url(guild_id, ticket.thread_id)
        created_at = discord_timestamp(ticket.created_at)
        title = _trim_embed_text(ticket.title, limit=60)
        lines = [
            f"`#{ticket.ticket_number}` [{title}]({thread_url})",
            f"статус: `{ticket.status.value}`",
            f"создано: {created_at}",
        ]
        if include_closed_at and ticket.closed_at is not None:
            lines.append(f"закрыто: {discord_timestamp(ticket.closed_at)}")
        return "\n".join(lines)

    embed.add_field(
        "Открытые обращения",
        _ticket_list_field(
            open_tickets,
            formatter=lambda ticket: format_ticket(ticket, include_closed_at=False),
            empty_text="Открытых обращений нет.",
            max_items=5,
        ),
        inline=False,
    )
    embed.add_field(
        "Последние закрытые",
        _ticket_list_field(
            closed_tickets,
            formatter=lambda ticket: format_ticket(ticket, include_closed_at=True),
            empty_text="Закрытых обращений пока нет.",
            max_items=5,
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
) -> str:
    if not tickets:
        return empty_text

    visible_tickets = tickets[:max_items]
    items = [formatter(ticket) for ticket in visible_tickets]
    hidden_count = len(tickets) - len(visible_tickets)
    if hidden_count > 0:
        items.append(f"Еще {hidden_count} не показано.")
    return "\n\n".join(items)


def _trim_embed_text(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}..."


def _format_support_roles(support_roles: list[SupportRole]) -> str:
    if not support_roles:
        return "не настроены"
    return ", ".join(f"<@&{role.role_id}>" for role in support_roles)
