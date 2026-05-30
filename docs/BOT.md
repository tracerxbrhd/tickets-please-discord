# Bot Behavior

Tickets! Please is a private Discord support ticket bot. It creates a support
panel, user-private ticket channels, per-ticket threads, a settings panel, and a
logs channel for operational events.

## Slash Commands

- `/tickets-setup`: creates or reuses the `Tickets! Please` category, `#поддержка`,
  `#tickets-logs`, and `#tickets-settings`; sends the support panel and settings
  panel; saves all channel and message IDs in PostgreSQL.
- `/tickets-status`: shows the saved configuration for the current guild.
- `/tickets-reset`: removes saved configuration and support roles from the database
  without deleting Discord channels.

The commands require the user to have `Manage Server`.

## Support Panel

The support panel uses persistent `hikari-miru` buttons:

- `Создать обращение`: validates that the click came from the saved active support
  panel, checks the open-ticket limit, opens a modal for topic and description,
  creates a private per-user channel when needed, creates a new thread for the
  ticket, stores the ticket in PostgreSQL, and writes creation events to the logs
  channel.
- `Мои обращения`: validates the panel and returns an ephemeral list of the user's
  open tickets plus the latest closed tickets, including ticket number, title,
  status, creation date, close date where applicable, and a thread link.

The view is unbound and persistent: it has `timeout=None`, explicit `custom_id`
values, and is registered again on every bot startup. Re-running `/tickets-setup`
edits the saved support message and restores the buttons if they were removed.

File uploads in modals are not implemented. The ticket thread tells users to attach
files as the next message, which is the current fallback path.

Each user can have up to 5 open tickets at a time. The bot checks the limit before
opening the creation modal and again before creating the Discord thread.

## Ticket Closure

Each ticket thread starts with a persistent `Закрыть обращение` button. The button:

- validates that the current thread belongs to an open ticket;
- allows closure by the ticket author, support roles, administrators, or members
  with channel/thread management permissions;
- asks for explicit modal confirmation by typing `закрыть`;
- sets the ticket status to `closed`, writes `closed_at` and `closed_by_id`, and
  records a `ticket_closed` event;
- removes the active close button, posts a final message, logs the event, and
  archives plus locks the thread.

Closed tickets are final and cannot be reopened.

## Settings Panel

The `#tickets-settings` message has a persistent role select for the support role.
Selecting a role:

- stores it in `support_roles`;
- updates the settings embed;
- grants the role access to `#tickets-logs`;
- grants the role access to existing user ticket channels;
- logs `support_role_assigned` to the logs channel.

Only users with `Manage Server` or `Administrator` can change the role. The settings
channel remains hidden from regular members. The `@everyone` role is rejected as a
support role to keep logs and private ticket channels from becoming public.
