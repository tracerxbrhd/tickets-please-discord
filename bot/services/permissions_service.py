"""Discord permission propagation service."""

from __future__ import annotations

import logging

import hikari
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import GuildSettings
from bot.database.repositories import UserTicketChannelRepository
from bot.utils.permissions import support_logs_channel_allow, support_ticket_channel_allow

LOGGER = logging.getLogger(__name__)


class PermissionsService:
    """Applies support-role overwrites to existing Discord resources."""

    def __init__(
        self,
        user_channel_repository: UserTicketChannelRepository | None = None,
    ) -> None:
        self._user_channel_repository = user_channel_repository or UserTicketChannelRepository()

    async def apply_support_roles(
        self,
        session: AsyncSession,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        settings: GuildSettings,
        old_role_ids: set[int],
        new_role_ids: set[int],
    ) -> None:
        """Apply support-role visibility to logs and user ticket channels."""

        removed_role_ids = old_role_ids - new_role_ids
        added_role_ids = new_role_ids

        target_channel_ids: list[int] = []
        if settings.logs_channel_id is not None:
            target_channel_ids.append(settings.logs_channel_id)

        for role_id in removed_role_ids:
            for channel_id in target_channel_ids:
                await self._delete_overwrite(rest, channel_id=channel_id, target_id=role_id)

        for role_id in added_role_ids:
            for channel_id in target_channel_ids:
                await self._edit_overwrite(
                    rest,
                    channel_id=channel_id,
                    role_id=role_id,
                    allow=support_logs_channel_allow(),
                )

        user_channels = await self._user_channel_repository.list_for_guild(session, guild_id)
        user_channel_ids = [record.channel_id for record in user_channels]

        for role_id in removed_role_ids:
            for channel_id in user_channel_ids:
                await self._delete_overwrite(rest, channel_id=channel_id, target_id=role_id)

        for role_id in added_role_ids:
            for channel_id in user_channel_ids:
                await self._edit_overwrite(
                    rest,
                    channel_id=channel_id,
                    role_id=role_id,
                    allow=support_ticket_channel_allow(),
                )

    async def _edit_overwrite(
        self,
        rest: hikari.api.RESTClient,
        *,
        channel_id: int,
        role_id: int,
        allow: hikari.Permissions,
    ) -> None:
        try:
            await rest.edit_permission_overwrite(
                channel_id,
                role_id,
                target_type=hikari.PermissionOverwriteType.ROLE,
                allow=allow,
                deny=hikari.Permissions.NONE,
            )
        except hikari.NotFoundError:
            LOGGER.warning("Cannot update permissions for missing channel %s", channel_id)
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to update overwrites for channel %s", channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected overwrite update for channel %s", channel_id)

    async def _delete_overwrite(
        self,
        rest: hikari.api.RESTClient,
        *,
        channel_id: int,
        target_id: int,
    ) -> None:
        try:
            await rest.delete_permission_overwrite(channel_id, target_id)
        except hikari.NotFoundError:
            return
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to delete overwrites for channel %s", channel_id)
        except hikari.BadRequestError:
            LOGGER.warning("Discord rejected overwrite deletion for channel %s", channel_id)
