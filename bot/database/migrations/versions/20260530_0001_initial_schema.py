"""Create initial ticket schema.

Revision ID: 20260530_0001
Revises:
Create Date: 2026-05-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


ticket_status = sa.Enum(
    "open",
    "in_progress",
    "waiting_user",
    "waiting_staff",
    "closed",
    name="ticket_status",
    native_enum=False,
    create_constraint=True,
)
ticket_event_type = sa.Enum(
    "setup_completed",
    "user_channel_created",
    "ticket_created",
    "ticket_closed",
    "ticket_status_changed",
    "attachment_added",
    "settings_updated",
    "support_role_assigned",
    "permission_denied",
    "system_channel_missing",
    "system_message_missing",
    "error",
    name="ticket_event_type",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "guild_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("support_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("logs_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("settings_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("support_message_id", sa.BigInteger(), nullable=True),
        sa.Column("settings_message_id", sa.BigInteger(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guild_settings")),
        sa.UniqueConstraint("guild_id", name=op.f("uq_guild_settings_guild_id")),
    )

    op.create_table(
        "support_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_support_roles")),
        sa.UniqueConstraint("guild_id", "role_id", name=op.f("uq_support_roles_guild_id_role_id")),
    )
    op.create_index(op.f("ix_support_roles_guild_id"), "support_roles", ["guild_id"], unique=False)

    op.create_table(
        "user_ticket_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_ticket_channels")),
        sa.UniqueConstraint(
            "guild_id",
            "channel_id",
            name=op.f("uq_user_ticket_channels_guild_id_channel_id"),
        ),
        sa.UniqueConstraint(
            "guild_id",
            "user_id",
            name=op.f("uq_user_ticket_channels_guild_id_user_id"),
        ),
    )
    op.create_index(
        op.f("ix_user_ticket_channels_guild_id"),
        "user_ticket_channels",
        ["guild_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_ticket_channels_user_id"),
        "user_ticket_channels",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", ticket_status, server_default="open", nullable=False),
        sa.Column("assigned_moderator_id", sa.BigInteger(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tickets")),
        sa.UniqueConstraint("guild_id", "thread_id", name=op.f("uq_tickets_guild_id_thread_id")),
        sa.UniqueConstraint(
            "guild_id",
            "ticket_number",
            name=op.f("uq_tickets_guild_id_ticket_number"),
        ),
    )
    op.create_index(op.f("ix_tickets_guild_id"), "tickets", ["guild_id"], unique=False)
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)
    op.create_index(op.f("ix_tickets_user_id"), "tickets", ["user_id"], unique=False)

    op.create_table(
        "ticket_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_ticket_attachments_ticket_id_tickets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_attachments")),
    )
    op.create_index(
        op.f("ix_ticket_attachments_ticket_id"),
        "ticket_attachments",
        ["ticket_id"],
        unique=False,
    )

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("event_type", ticket_event_type, nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_ticket_events_ticket_id_tickets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_events")),
    )
    op.create_index(
        op.f("ix_ticket_events_ticket_id"),
        "ticket_events",
        ["ticket_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ticket_events_ticket_id"), table_name="ticket_events")
    op.drop_table("ticket_events")
    op.drop_index(op.f("ix_ticket_attachments_ticket_id"), table_name="ticket_attachments")
    op.drop_table("ticket_attachments")
    op.drop_index(op.f("ix_tickets_user_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_guild_id"), table_name="tickets")
    op.drop_table("tickets")
    op.drop_index(op.f("ix_user_ticket_channels_user_id"), table_name="user_ticket_channels")
    op.drop_index(op.f("ix_user_ticket_channels_guild_id"), table_name="user_ticket_channels")
    op.drop_table("user_ticket_channels")
    op.drop_index(op.f("ix_support_roles_guild_id"), table_name="support_roles")
    op.drop_table("support_roles")
    op.drop_table("guild_settings")
