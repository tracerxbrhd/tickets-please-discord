"""Guild setup orchestration service for `/tickets-setup`."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

import hikari
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import GuildSettings, SupportRole
from bot.database.repositories import GuildSettingsRepository, SupportRoleRepository
from bot.ui.embeds import build_settings_panel_embed, build_support_panel_embed
from bot.ui.views import build_settings_panel_components, build_support_panel_components
from bot.utils.permissions import private_text_channel_overwrites

CATEGORY_NAME = "Tickets! Please"
SUPPORT_CHANNEL_NAME = "поддержка"
LOGS_CHANNEL_NAME = "tickets-logs"
SETTINGS_CHANNEL_NAME = "tickets-settings"

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SetupResult:
    """Summary of resources created or reused during guild setup."""

    guild_id: int
    category_id: int
    support_channel_id: int
    logs_channel_id: int
    settings_channel_id: int
    support_message_id: int
    settings_message_id: int
    created_resources: list[str] = field(default_factory=list)
    reused_resources: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _ChannelBundle:
    category: hikari.GuildCategory
    support_channel: hikari.GuildTextChannel
    logs_channel: hikari.GuildTextChannel
    settings_channel: hikari.GuildTextChannel


class SetupService:
    """Creates and persists the basic Discord resources for a guild."""

    def __init__(
        self,
        settings_repository: GuildSettingsRepository | None = None,
        support_role_repository: SupportRoleRepository | None = None,
    ) -> None:
        self._settings_repository = settings_repository or GuildSettingsRepository()
        self._support_role_repository = support_role_repository or SupportRoleRepository()

    async def setup_guild(
        self,
        session: AsyncSession,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
    ) -> SetupResult:
        """Create or update the ticket system scaffold for a guild."""

        settings = await self._settings_repository.get_by_guild_id(session, guild_id)
        bot_user = await rest.fetch_my_user()
        created: list[str] = []
        reused: list[str] = []

        channels = await self._ensure_channels(
            rest,
            guild_id=guild_id,
            bot_user_id=int(bot_user.id),
            settings=settings,
            created=created,
            reused=reused,
        )

        support_message = await self._upsert_support_message(
            rest,
            guild_id=guild_id,
            support_channel=channels.support_channel,
            support_message_id=settings.support_message_id if settings else None,
            created=created,
            reused=reused,
        )

        settings_record = await self._persist_settings(
            session,
            existing=settings,
            guild_id=guild_id,
            category_id=int(channels.category.id),
            support_channel_id=int(channels.support_channel.id),
            logs_channel_id=int(channels.logs_channel.id),
            settings_channel_id=int(channels.settings_channel.id),
            support_message_id=int(support_message.id),
        )

        settings_message = await self._upsert_settings_message(
            rest,
            guild_id=guild_id,
            settings_channel=channels.settings_channel,
            settings_record=settings_record,
            support_roles=await self._support_role_repository.list_for_guild(session, guild_id),
            settings_message_id=settings.settings_message_id if settings else None,
            created=created,
            reused=reused,
        )

        settings_record = await self._settings_repository.update(
            session,
            settings_record,
            settings_message_id=int(settings_message.id),
            is_enabled=True,
        )

        return SetupResult(
            guild_id=guild_id,
            category_id=settings_record.category_id or int(channels.category.id),
            support_channel_id=(
                settings_record.support_channel_id or int(channels.support_channel.id)
            ),
            logs_channel_id=settings_record.logs_channel_id or int(channels.logs_channel.id),
            settings_channel_id=(
                settings_record.settings_channel_id or int(channels.settings_channel.id)
            ),
            support_message_id=settings_record.support_message_id or int(support_message.id),
            settings_message_id=settings_record.settings_message_id or int(settings_message.id),
            created_resources=created,
            reused_resources=reused,
        )

    async def _ensure_channels(
        self,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        bot_user_id: int,
        settings: GuildSettings | None,
        created: list[str],
        reused: list[str],
    ) -> _ChannelBundle:
        category = await self._get_or_create_category(
            rest,
            guild_id=guild_id,
            category_id=settings.category_id if settings else None,
            created=created,
            reused=reused,
        )
        support_channel = await self._get_or_create_text_channel(
            rest,
            guild_id=guild_id,
            channel_id=settings.support_channel_id if settings else None,
            name=SUPPORT_CHANNEL_NAME,
            parent_id=int(category.id),
            permission_overwrites=None,
            created=created,
            reused=reused,
        )
        private_overwrites = private_text_channel_overwrites(
            guild_id=guild_id,
            bot_user_id=bot_user_id,
        )
        logs_channel = await self._get_or_create_text_channel(
            rest,
            guild_id=guild_id,
            channel_id=settings.logs_channel_id if settings else None,
            name=LOGS_CHANNEL_NAME,
            parent_id=int(category.id),
            permission_overwrites=private_overwrites,
            created=created,
            reused=reused,
        )
        settings_channel = await self._get_or_create_text_channel(
            rest,
            guild_id=guild_id,
            channel_id=settings.settings_channel_id if settings else None,
            name=SETTINGS_CHANNEL_NAME,
            parent_id=int(category.id),
            permission_overwrites=private_overwrites,
            created=created,
            reused=reused,
        )
        return _ChannelBundle(
            category=category,
            support_channel=support_channel,
            logs_channel=logs_channel,
            settings_channel=settings_channel,
        )

    async def _get_or_create_category(
        self,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        category_id: int | None,
        created: list[str],
        reused: list[str],
    ) -> hikari.GuildCategory:
        if category_id is not None:
            existing = await self._fetch_channel(rest, category_id, hikari.GuildCategory)
            if existing is not None:
                reused.append(f"category {CATEGORY_NAME}")
                return existing

        category = await rest.create_guild_category(guild_id, name=CATEGORY_NAME)
        created.append(f"category {CATEGORY_NAME}")
        return category

    async def _get_or_create_text_channel(
        self,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        channel_id: int | None,
        name: str,
        parent_id: int,
        permission_overwrites: list[hikari.PermissionOverwrite] | None,
        created: list[str],
        reused: list[str],
    ) -> hikari.GuildTextChannel:
        if channel_id is not None:
            existing = await self._fetch_channel(rest, channel_id, hikari.GuildTextChannel)
            if existing is not None:
                reused.append(f"channel #{name}")
                return existing

        channel = await rest.create_guild_text_channel(
            guild_id,
            name=name,
            category=parent_id,
            permission_overwrites=permission_overwrites,
        )
        created.append(f"channel #{name}")
        return channel

    async def _fetch_channel(
        self,
        rest: hikari.api.RESTClient,
        channel_id: int,
        channel_type: type[hikari.GuildCategory] | type[hikari.GuildTextChannel],
    ) -> hikari.GuildCategory | hikari.GuildTextChannel | None:
        try:
            channel = await rest.fetch_channel(channel_id)
        except hikari.NotFoundError:
            return None
        except hikari.ForbiddenError:
            LOGGER.warning("Missing permission to fetch saved setup channel %s", channel_id)
            return None

        if isinstance(channel, channel_type):
            return channel
        return None

    async def _upsert_support_message(
        self,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        support_channel: hikari.GuildTextChannel,
        support_message_id: int | None,
        created: list[str],
        reused: list[str],
    ) -> hikari.Message:
        return await self._upsert_message(
            rest,
            guild_id=guild_id,
            channel_id=int(support_channel.id),
            message_id=support_message_id,
            embed=build_support_panel_embed(),
            components=build_support_panel_components(),
            resource_name="support panel message",
            created=created,
            reused=reused,
        )

    async def _upsert_settings_message(
        self,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        settings_channel: hikari.GuildTextChannel,
        settings_record: GuildSettings,
        support_roles: list[SupportRole],
        settings_message_id: int | None,
        created: list[str],
        reused: list[str],
    ) -> hikari.Message:
        return await self._upsert_message(
            rest,
            guild_id=guild_id,
            channel_id=int(settings_channel.id),
            message_id=settings_message_id,
            embed=build_settings_panel_embed(settings_record, support_roles=support_roles),
            components=build_settings_panel_components(),
            resource_name="settings panel message",
            created=created,
            reused=reused,
        )

    async def _upsert_message(
        self,
        rest: hikari.api.RESTClient,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int | None,
        embed: hikari.Embed,
        components: Sequence[hikari.api.ComponentBuilder],
        resource_name: str,
        created: list[str],
        reused: list[str],
    ) -> hikari.Message:
        del guild_id

        if message_id is not None:
            try:
                await rest.fetch_message(channel_id, message_id)
                message = await rest.edit_message(
                    channel_id,
                    message_id,
                    embed=embed,
                    components=components,
                )
            except hikari.NotFoundError:
                pass
            else:
                reused.append(resource_name)
                return message

        message = await rest.create_message(channel_id, embed=embed, components=components)
        created.append(resource_name)
        return message

    async def _persist_settings(
        self,
        session: AsyncSession,
        *,
        existing: GuildSettings | None,
        guild_id: int,
        category_id: int,
        support_channel_id: int,
        logs_channel_id: int,
        settings_channel_id: int,
        support_message_id: int,
    ) -> GuildSettings:
        fields = {
            "category_id": category_id,
            "support_channel_id": support_channel_id,
            "logs_channel_id": logs_channel_id,
            "settings_channel_id": settings_channel_id,
            "support_message_id": support_message_id,
            "is_enabled": True,
        }
        if existing is None:
            return await self._settings_repository.create(session, guild_id=guild_id, **fields)

        return await self._settings_repository.update(session, existing, **fields)
