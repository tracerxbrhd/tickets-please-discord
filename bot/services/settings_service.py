"""Guild ticket settings service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import GuildSettings, SupportRole
from bot.database.repositories import GuildSettingsRepository, SupportRoleRepository


@dataclass(slots=True)
class ResetResult:
    """Result of a non-destructive guild settings reset."""

    was_configured: bool
    logs_channel_id: int | None


@dataclass(slots=True)
class SupportRoleUpdateResult:
    """Result of replacing the configured support role."""

    settings: GuildSettings | None
    old_role_ids: set[int]
    new_role_ids: set[int]
    support_roles: list[SupportRole]


class SettingsService:
    """Service API for guild-level ticket settings."""

    def __init__(
        self,
        settings_repository: GuildSettingsRepository | None = None,
        support_role_repository: SupportRoleRepository | None = None,
    ) -> None:
        self._settings_repository = settings_repository or GuildSettingsRepository()
        self._support_role_repository = support_role_repository or SupportRoleRepository()

    async def get_settings(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
    ) -> GuildSettings | None:
        """Return saved settings for a guild."""

        return await self._settings_repository.get_by_guild_id(session, guild_id)

    async def list_support_roles(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
    ) -> list[SupportRole]:
        """Return configured support roles for a guild."""

        return await self._support_role_repository.list_for_guild(session, guild_id)

    async def set_support_role(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
        role_id: int,
    ) -> SupportRoleUpdateResult:
        """Replace current support roles with a single selected role."""

        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        existing_roles = await self._support_role_repository.list_for_guild(session, guild_id)
        old_role_ids = {role.role_id for role in existing_roles}

        await self._support_role_repository.clear_for_guild(session, guild_id)
        role = await self._support_role_repository.add(
            session,
            guild_id=guild_id,
            role_id=role_id,
        )
        await session.flush()

        return SupportRoleUpdateResult(
            settings=settings,
            old_role_ids=old_role_ids,
            new_role_ids={role_id},
            support_roles=[role],
        )

    async def reset_settings(
        self,
        session: AsyncSession,
        *,
        guild_id: int,
    ) -> ResetResult:
        """Forget saved settings and support roles without deleting Discord channels."""

        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        logs_channel_id = settings.logs_channel_id if settings else None

        await self._support_role_repository.clear_for_guild(session, guild_id)
        was_configured = await self._settings_repository.delete_by_guild_id(session, guild_id)
        await session.flush()

        return ResetResult(was_configured=was_configured, logs_channel_id=logs_channel_id)
