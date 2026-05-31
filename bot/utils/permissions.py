"""Shared permission helper functions."""

from __future__ import annotations

import hikari

SETUP_USER_PERMISSIONS = hikari.Permissions.MANAGE_GUILD
SETUP_BOT_PERMISSIONS = (
    hikari.Permissions.MANAGE_CHANNELS
    | hikari.Permissions.MANAGE_THREADS
    | hikari.Permissions.VIEW_CHANNEL
    | hikari.Permissions.SEND_MESSAGES
    | hikari.Permissions.EMBED_LINKS
    | hikari.Permissions.READ_MESSAGE_HISTORY
    | hikari.Permissions.CREATE_PUBLIC_THREADS
)


def missing_permissions(
    actual: hikari.Permissions,
    required: hikari.Permissions,
) -> hikari.Permissions:
    """Return the subset of required permissions missing from actual permissions."""

    if actual & hikari.Permissions.ADMINISTRATOR:
        return hikari.Permissions.NONE
    return required & ~actual


def format_permissions(permissions: hikari.Permissions) -> str:
    """Render a permission bitfield into a compact readable list."""

    if permissions == hikari.Permissions.NONE:
        return "none"

    names: list[str] = []
    for permission in hikari.Permissions:
        if permission & permissions:
            names.append((permission.name or str(int(permission))).lower())

    return ", ".join(names)


def member_permissions(member: object) -> hikari.Permissions:
    """Extract resolved guild permissions from a Hikari member-like object."""

    permissions = getattr(member, "permissions", hikari.Permissions.NONE)
    if permissions is hikari.UNDEFINED or permissions is None:
        return hikari.Permissions.NONE
    return permissions


def member_role_ids(member: object) -> set[int]:
    """Extract role IDs from a Hikari member-like object."""

    role_ids = getattr(member, "role_ids", ()) or ()
    return {int(role_id) for role_id in role_ids}


def private_text_channel_overwrites(
    *,
    guild_id: int,
    bot_user_id: int,
) -> list[hikari.PermissionOverwrite]:
    """Build overwrites for logs/settings channels hidden from regular users."""

    bot_allow = (
        hikari.Permissions.VIEW_CHANNEL
        | hikari.Permissions.SEND_MESSAGES
        | hikari.Permissions.EMBED_LINKS
        | hikari.Permissions.READ_MESSAGE_HISTORY
        | hikari.Permissions.MANAGE_CHANNELS
        | hikari.Permissions.MANAGE_THREADS
        | hikari.Permissions.CREATE_PUBLIC_THREADS
    )
    return [
        hikari.PermissionOverwrite(
            id=guild_id,
            type=hikari.PermissionOverwriteType.ROLE,
            allow=hikari.Permissions.NONE,
            deny=(
                hikari.Permissions.VIEW_CHANNEL
                | hikari.Permissions.SEND_MESSAGES
                | hikari.Permissions.CREATE_PUBLIC_THREADS
            ),
        ),
        hikari.PermissionOverwrite(
            id=bot_user_id,
            type=hikari.PermissionOverwriteType.MEMBER,
            allow=bot_allow,
            deny=hikari.Permissions.NONE,
        ),
    ]


def support_logs_channel_allow() -> hikari.Permissions:
    """Read-only permissions granted to support roles in the logs channel."""

    return (
        hikari.Permissions.VIEW_CHANNEL
        | hikari.Permissions.EMBED_LINKS
        | hikari.Permissions.READ_MESSAGE_HISTORY
    )


def support_ticket_channel_allow() -> hikari.Permissions:
    """Permissions granted to support roles in user ticket channels."""

    return (
        hikari.Permissions.VIEW_CHANNEL
        | hikari.Permissions.SEND_MESSAGES
        | hikari.Permissions.EMBED_LINKS
        | hikari.Permissions.READ_MESSAGE_HISTORY
        | hikari.Permissions.MANAGE_THREADS
        | hikari.Permissions.CREATE_PUBLIC_THREADS
        | hikari.Permissions.ATTACH_FILES
    )


def user_ticket_channel_overwrites(
    *,
    guild_id: int,
    user_id: int,
    bot_user_id: int,
    support_role_ids: list[int],
) -> list[hikari.PermissionOverwrite]:
    """Build overwrites for a user's private ticket channel."""

    bot_allow = (
        hikari.Permissions.VIEW_CHANNEL
        | hikari.Permissions.SEND_MESSAGES
        | hikari.Permissions.EMBED_LINKS
        | hikari.Permissions.READ_MESSAGE_HISTORY
        | hikari.Permissions.MANAGE_CHANNELS
        | hikari.Permissions.MANAGE_THREADS
        | hikari.Permissions.CREATE_PUBLIC_THREADS
        | hikari.Permissions.ATTACH_FILES
    )
    participant_allow = (
        hikari.Permissions.VIEW_CHANNEL
        | hikari.Permissions.SEND_MESSAGES
        | hikari.Permissions.READ_MESSAGE_HISTORY
        | hikari.Permissions.CREATE_PUBLIC_THREADS
        | hikari.Permissions.ATTACH_FILES
    )
    support_allow = support_ticket_channel_allow()

    overwrites = [
        hikari.PermissionOverwrite(
            id=guild_id,
            type=hikari.PermissionOverwriteType.ROLE,
            allow=hikari.Permissions.NONE,
            deny=hikari.Permissions.VIEW_CHANNEL,
        ),
        hikari.PermissionOverwrite(
            id=bot_user_id,
            type=hikari.PermissionOverwriteType.MEMBER,
            allow=bot_allow,
            deny=hikari.Permissions.NONE,
        ),
        hikari.PermissionOverwrite(
            id=user_id,
            type=hikari.PermissionOverwriteType.MEMBER,
            allow=participant_allow,
            deny=hikari.Permissions.NONE,
        ),
    ]
    overwrites.extend(
        hikari.PermissionOverwrite(
            id=role_id,
            type=hikari.PermissionOverwriteType.ROLE,
            allow=support_allow,
            deny=hikari.Permissions.NONE,
        )
        for role_id in support_role_ids
    )
    return overwrites
