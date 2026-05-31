"""Add ticket assignment and log thread fields.

Revision ID: 20260531_0003
Revises: 20260531_0002
Create Date: 2026-05-31 10:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260531_0003"
down_revision = "20260531_0002"
branch_labels = None
depends_on = None

EVENT_TYPES = (
    "setup_completed",
    "user_channel_created",
    "ticket_created",
    "ticket_claimed",
    "ticket_closed",
    "ticket_status_changed",
    "attachment_added",
    "settings_updated",
    "support_role_assigned",
    "permission_denied",
    "system_channel_missing",
    "system_message_missing",
    "error",
)
OLD_EVENT_TYPES = tuple(event for event in EVENT_TYPES if event != "ticket_claimed")


def _event_type_check(event_types: tuple[str, ...]) -> str:
    values = ", ".join(f"'{event_type}'" for event_type in event_types)
    return f"event_type IN ({values})"


def upgrade() -> None:
    op.add_column("tickets", sa.Column("log_thread_id", sa.BigInteger(), nullable=True))
    op.add_column("tickets", sa.Column("close_reason", sa.Text(), nullable=True))
    op.execute(
        "ALTER TABLE ticket_events "
        "DROP CONSTRAINT IF EXISTS ck_ticket_events_ticket_event_type"
    )
    op.execute("ALTER TABLE ticket_events DROP CONSTRAINT IF EXISTS ticket_event_type")
    op.create_check_constraint(
        "ticket_event_type",
        "ticket_events",
        _event_type_check(EVENT_TYPES),
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ticket_events "
        "DROP CONSTRAINT IF EXISTS ck_ticket_events_ticket_event_type"
    )
    op.execute("ALTER TABLE ticket_events DROP CONSTRAINT IF EXISTS ticket_event_type")
    op.create_check_constraint(
        "ticket_event_type",
        "ticket_events",
        _event_type_check(OLD_EVENT_TYPES),
    )
    op.drop_column("tickets", "close_reason")
    op.drop_column("tickets", "log_thread_id")
