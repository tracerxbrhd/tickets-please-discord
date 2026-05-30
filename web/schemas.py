"""Response schemas for the web admin API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Liveness and dependency status for the admin API."""

    status: str
    database: str
    environment: str


class GuildSettingsView(BaseModel):
    """Read model for saved guild ticket settings."""

    model_config = ConfigDict(from_attributes=True)

    guild_id: int
    category_id: int | None
    support_channel_id: int | None
    logs_channel_id: int | None
    settings_channel_id: int | None
    support_message_id: int | None
    settings_message_id: int | None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class TicketSummary(BaseModel):
    """Compact read model for ticket list views."""

    id: int
    guild_id: int
    user_id: int
    channel_id: int
    thread_id: int
    ticket_number: int
    title: str
    status: str
    created_at: datetime
    closed_at: datetime | None
    closed_by_id: int | None


class GuildSummary(BaseModel):
    """Guild row returned by the admin dashboard list endpoint."""

    settings: GuildSettingsView
    support_role_ids: list[int]
    ticket_counts: dict[str, int]


class GuildDetail(GuildSummary):
    """Guild details returned by the admin detail endpoint."""

    recent_tickets: list[TicketSummary]
