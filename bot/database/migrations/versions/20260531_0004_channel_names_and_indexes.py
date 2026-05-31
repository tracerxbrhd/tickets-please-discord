"""Add configurable setup channel names and lookup indexes.

Revision ID: 20260531_0004
Revises: 20260531_0003
Create Date: 2026-05-31 13:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260531_0004"
down_revision = "20260531_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "guild_settings",
        sa.Column(
            "category_name",
            sa.String(length=100),
            server_default="Tickets! Please",
            nullable=False,
        ),
    )
    op.add_column(
        "guild_settings",
        sa.Column(
            "support_channel_name",
            sa.String(length=100),
            server_default="support",
            nullable=False,
        ),
    )
    op.add_column(
        "guild_settings",
        sa.Column(
            "logs_channel_name",
            sa.String(length=100),
            server_default="tickets-logs",
            nullable=False,
        ),
    )
    op.add_column(
        "guild_settings",
        sa.Column(
            "settings_channel_name",
            sa.String(length=100),
            server_default="tickets-settings",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_tickets_guild_user_status",
        "tickets",
        ["guild_id", "user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_tickets_guild_status_created_at",
        "tickets",
        ["guild_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_events_ticket_created_at",
        "ticket_events",
        ["ticket_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_events_ticket_created_at", table_name="ticket_events")
    op.drop_index("ix_tickets_guild_status_created_at", table_name="tickets")
    op.drop_index("ix_tickets_guild_user_status", table_name="tickets")
    op.drop_column("guild_settings", "settings_channel_name")
    op.drop_column("guild_settings", "logs_channel_name")
    op.drop_column("guild_settings", "support_channel_name")
    op.drop_column("guild_settings", "category_name")
