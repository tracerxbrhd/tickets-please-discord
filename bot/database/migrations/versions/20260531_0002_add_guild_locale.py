"""Add locale to guild settings.

Revision ID: 20260531_0002
Revises: 20260530_0001
Create Date: 2026-05-31 00:02:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260531_0002"
down_revision = "20260530_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "guild_settings",
        sa.Column("locale", sa.String(length=12), server_default="en", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("guild_settings", "locale")
