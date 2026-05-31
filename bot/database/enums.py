"""Database-backed domain enums."""

from __future__ import annotations

from enum import StrEnum


class TicketStatus(StrEnum):
    """Lifecycle statuses supported by ticket records."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    WAITING_STAFF = "waiting_staff"
    CLOSED = "closed"


class TicketEventType(StrEnum):
    """Event types used for ticket history and audit trails."""

    SETUP_COMPLETED = "setup_completed"
    USER_CHANNEL_CREATED = "user_channel_created"
    TICKET_CREATED = "ticket_created"
    TICKET_CLAIMED = "ticket_claimed"
    TICKET_CLOSED = "ticket_closed"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    ATTACHMENT_ADDED = "attachment_added"
    SETTINGS_UPDATED = "settings_updated"
    SUPPORT_ROLE_ASSIGNED = "support_role_assigned"
    PERMISSION_DENIED = "permission_denied"
    SYSTEM_CHANNEL_MISSING = "system_channel_missing"
    SYSTEM_MESSAGE_MISSING = "system_message_missing"
    ERROR = "error"
