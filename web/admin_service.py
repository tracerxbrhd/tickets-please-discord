"""Read-only service for the web admin API."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import TicketStatus
from bot.database.models import GuildSettings, Ticket
from bot.database.repositories import (
    GuildSettingsRepository,
    SupportRoleRepository,
    TicketRepository,
)
from web.schemas import GuildDetail, GuildSettingsView, GuildSummary, TicketSummary


class AdminReadService:
    """Builds admin dashboard read models from repository data."""

    def __init__(
        self,
        settings_repository: GuildSettingsRepository | None = None,
        support_role_repository: SupportRoleRepository | None = None,
        ticket_repository: TicketRepository | None = None,
    ) -> None:
        self._settings_repository = settings_repository or GuildSettingsRepository()
        self._support_role_repository = support_role_repository or SupportRoleRepository()
        self._ticket_repository = ticket_repository or TicketRepository()

    async def list_guilds(self, session: AsyncSession) -> list[GuildSummary]:
        """Return all configured guilds with support roles and ticket counts."""

        guild_settings = await self._settings_repository.list_all(session)
        summaries: list[GuildSummary] = []
        for settings in guild_settings:
            summaries.append(
                await self._build_guild_summary(session, settings=settings)
            )
        return summaries

    async def get_guild(self, session: AsyncSession, *, guild_id: int) -> GuildDetail | None:
        """Return a detailed admin view for one configured guild."""

        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        if settings is None:
            return None

        summary = await self._build_guild_summary(session, settings=settings)
        recent_tickets = await self._ticket_repository.list_recent_for_guild(
            session,
            guild_id=guild_id,
            limit=20,
        )
        return GuildDetail(
            settings=summary.settings,
            support_role_ids=summary.support_role_ids,
            ticket_counts=summary.ticket_counts,
            recent_tickets=[self._ticket_summary(ticket) for ticket in recent_tickets],
        )

    async def _build_guild_summary(
        self,
        session: AsyncSession,
        *,
        settings: GuildSettings,
    ) -> GuildSummary:
        support_roles = await self._support_role_repository.list_for_guild(
            session,
            settings.guild_id,
        )
        raw_counts = await self._ticket_repository.count_by_status_for_guild(
            session,
            guild_id=settings.guild_id,
        )
        return GuildSummary(
            settings=GuildSettingsView.model_validate(settings),
            support_role_ids=[role.role_id for role in support_roles],
            ticket_counts=self._ticket_counts(raw_counts),
        )

    def _ticket_counts(self, raw_counts: dict[TicketStatus, int]) -> dict[str, int]:
        return {
            status.value: raw_counts.get(status, 0)
            for status in TicketStatus
        }

    def _ticket_summary(self, ticket: Ticket) -> TicketSummary:
        return TicketSummary(
            id=ticket.id,
            guild_id=ticket.guild_id,
            user_id=ticket.user_id,
            channel_id=ticket.channel_id,
            thread_id=ticket.thread_id,
            ticket_number=ticket.ticket_number,
            title=ticket.title,
            status=ticket.status.value,
            created_at=ticket.created_at,
            closed_at=ticket.closed_at,
            closed_by_id=ticket.closed_by_id,
        )
