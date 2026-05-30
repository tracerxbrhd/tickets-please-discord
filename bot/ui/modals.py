"""Modal definitions for ticket creation and settings updates."""

from __future__ import annotations

import logging

import hikari
import miru

from bot.database.models import Ticket
from bot.ui.embeds import (
    build_panel_error_embed,
    build_ticket_closed_response_embed,
    build_ticket_closed_thread_embed,
    build_ticket_created_response_embed,
    build_ticket_thread_embed,
)
from bot.utils.permissions import member_permissions, member_role_ids

LOGGER = logging.getLogger(__name__)


class TicketCreateModal(miru.Modal, title="Создать обращение"):
    """Modal used to collect the initial ticket title and description."""

    subject = miru.TextInput(
        label="Тема обращения",
        placeholder="Кратко опишите тему",
        min_length=3,
        max_length=120,
        required=True,
    )
    description = miru.TextInput(
        label="Описание проблемы",
        placeholder="Опишите проблему и что уже пробовали сделать",
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=10,
        max_length=1500,
        required=True,
    )

    def __init__(
        self,
        *,
        guild_id: int,
        panel_channel_id: int,
        panel_message_id: int,
    ) -> None:
        super().__init__(timeout=300)
        self._guild_id = guild_id
        self._panel_channel_id = panel_channel_id
        self._panel_message_id = panel_message_id

    async def callback(self, ctx: miru.ModalContext) -> None:
        """Create the ticket after the user submits the modal."""

        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        title = str(self.subject.value or "").strip()
        description = str(self.description.value or "").strip()
        if len(title) < 3 or len(description) < 10:
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Заполните тему и описание обращения подробнее."
                )
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        try:
            async with runtime.database.session() as session:
                result = await runtime.ticket_service.create_ticket(
                    session,
                    runtime.bot.rest,
                    guild_id=self._guild_id,
                    panel_channel_id=self._panel_channel_id,
                    panel_message_id=self._panel_message_id,
                    user_id=int(ctx.user.id),
                    title=title,
                    description=description,
                )

            if not result.validation.is_valid or result.ticket is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        result.validation.reason or "Не удалось создать обращение."
                    )
                )
                return

            from bot.ui.views import build_ticket_thread_components

            try:
                await runtime.bot.rest.create_message(
                    result.ticket.thread_id,
                    embed=build_ticket_thread_embed(result.ticket),
                    components=build_ticket_thread_components(),
                    user_mentions=[result.ticket.user_id],
                )
            except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
                LOGGER.exception(
                    "Failed to send first ticket message for ticket %s",
                    result.ticket.id,
                )
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        "Обращение создано, но бот не смог отправить сообщение в ветку."
                    )
                )
                return

            await runtime.logging_service.send_ticket_created(
                runtime.bot.rest,
                logs_channel_id=result.validation.settings.logs_channel_id
                if result.validation.settings
                else None,
                ticket=result.ticket,
                guild_id=self._guild_id,
            )
            if result.user_channel_created:
                await runtime.logging_service.send_system_event(
                    runtime.bot.rest,
                    logs_channel_id=result.validation.settings.logs_channel_id
                    if result.validation.settings
                    else None,
                    event_type="user_channel_created",
                    actor_id=int(ctx.user.id),
                    description=(
                        "Created private ticket channel "
                        f"<#{result.user_channel_id}> for <@{ctx.user.id}>."
                    ),
                )
            await ctx.edit_response(
                embed=build_ticket_created_response_embed(
                    result.ticket,
                    guild_id=self._guild_id,
                )
            )
        except hikari.ForbiddenError:
            LOGGER.exception("Discord denied ticket creation in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Боту не хватает прав для создания канала или ветки обращения."
                )
            )
        except hikari.BadRequestError:
            LOGGER.exception("Discord rejected ticket creation in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Discord отклонил создание обращения. Подробности записаны в логи бота."
                )
            )
        except Exception:
            LOGGER.exception("Unexpected ticket creation error in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Не удалось создать обращение. Подробности записаны в логи бота."
                )
            )


class TicketCloseConfirmModal(miru.Modal, title="Закрыть обращение"):
    """Modal used to confirm irreversible ticket closure."""

    confirmation = miru.TextInput(
        label="Подтверждение",
        placeholder="Введите: закрыть",
        min_length=5,
        max_length=20,
        required=True,
    )

    def __init__(
        self,
        *,
        guild_id: int,
        thread_id: int,
        ticket_message_id: int,
    ) -> None:
        super().__init__(timeout=120)
        self._guild_id = guild_id
        self._thread_id = thread_id
        self._ticket_message_id = ticket_message_id

    async def callback(self, ctx: miru.ModalContext) -> None:
        """Close a ticket after explicit user confirmation."""

        await ctx.defer(
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            flags=hikari.MessageFlag.EPHEMERAL,
        )

        if str(self.confirmation.value or "").strip().casefold() not in {"закрыть", "close"}:
            await ctx.edit_response(
                embed=build_panel_error_embed("Закрытие отменено: подтверждение не совпало.")
            )
            return

        from bot.runtime import get_runtime

        runtime = get_runtime()
        member = getattr(ctx, "member", None)
        try:
            async with runtime.database.session() as session:
                result = await runtime.ticket_service.close_ticket(
                    session,
                    guild_id=self._guild_id,
                    thread_id=self._thread_id,
                    actor_id=int(ctx.user.id),
                    actor_role_ids=member_role_ids(member),
                    actor_permissions=member_permissions(member),
                )

            if not result.validation.is_valid or result.ticket is None:
                await ctx.edit_response(
                    embed=build_panel_error_embed(
                        result.validation.reason or "Не удалось закрыть обращение."
                    )
                )
                return

            await self._remove_close_button(runtime.bot.rest, result.ticket)
            await self._send_closed_thread_message(runtime.bot.rest, result.ticket)
            archived = await self._archive_thread(runtime.bot.rest, result.ticket.thread_id)

            await runtime.logging_service.send_ticket_closed(
                runtime.bot.rest,
                logs_channel_id=result.validation.settings.logs_channel_id
                if result.validation.settings
                else None,
                ticket=result.ticket,
                guild_id=self._guild_id,
            )
            await ctx.edit_response(
                embed=build_ticket_closed_response_embed(result.ticket, archived=archived)
            )
        except hikari.ForbiddenError:
            LOGGER.exception("Discord denied ticket closure in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Боту не хватает прав для закрытия или архивирования обращения."
                )
            )
        except hikari.BadRequestError:
            LOGGER.exception("Discord rejected ticket closure in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Discord отклонил закрытие обращения. Подробности записаны в логи бота."
                )
            )
        except Exception:
            LOGGER.exception("Unexpected ticket closure error in guild %s", self._guild_id)
            await ctx.edit_response(
                embed=build_panel_error_embed(
                    "Не удалось закрыть обращение. Подробности записаны в логи бота."
                )
            )

    async def _remove_close_button(
        self,
        rest: hikari.api.RESTClient,
        ticket: Ticket,
    ) -> None:
        try:
            await rest.edit_message(
                self._thread_id,
                self._ticket_message_id,
                components=[],
            )
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to remove close button for ticket %s", ticket.id)

    async def _send_closed_thread_message(
        self,
        rest: hikari.api.RESTClient,
        ticket: Ticket,
    ) -> None:
        try:
            await rest.create_message(
                ticket.thread_id,
                embed=build_ticket_closed_thread_embed(ticket),
            )
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to send closed message for ticket %s", ticket.id)

    async def _archive_thread(self, rest: hikari.api.RESTClient, thread_id: int) -> bool:
        try:
            await rest.edit_channel(thread_id, archived=True, locked=True)
        except (hikari.ForbiddenError, hikari.NotFoundError, hikari.BadRequestError):
            LOGGER.exception("Failed to archive ticket thread %s", thread_id)
            return False
        return True
