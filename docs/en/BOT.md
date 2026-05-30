# Bot Behavior

**Language:** English | [Русский](../ru/BOT.md)

Tickets! Please creates Discord support tickets with a public support panel, private
user ticket channels, per-ticket threads, a settings panel, and a logs channel.

## Slash Commands

- `/tickets-setup`: creates or reuses the `Tickets! Please` category, `#support`,
  `#tickets-logs`, and `#tickets-settings`; sends the support panel and settings
  panel; saves all channel and message IDs in PostgreSQL.
- `/tickets-status`: shows the saved configuration for the current guild.
- `/tickets-reset`: removes saved configuration and support roles from the database
  without deleting Discord channels.

The commands require `Manage Server`.

## Support Panel

- `Create ticket`: validates the saved support panel, checks the open-ticket limit,
  opens a modal, creates a private per-user channel when needed, creates a thread,
  stores the ticket, and writes creation events to the logs channel.
- `My tickets`: returns an ephemeral list of the user's open tickets and latest
  closed tickets.

Each user can have up to 5 open tickets at a time.

## Ticket Channels And Threads

Private ticket channels are named from the user's account name, for example
`ticket-jane-doe`. The user's Discord ID remains the database key, so a rename does
not create a second stored channel record.

Each ticket is created as a thread inside the user's private ticket channel. The
configured support role is mentioned in the first ticket thread message so
moderators can jump into the thread. Discord permission overwrites on the parent
ticket channel give the support role access to the thread.

## Ticket Closure

Each ticket thread starts with a persistent close button. The button:

- validates that the current thread belongs to an open ticket;
- allows closure by the ticket author, support roles, administrators, or members
  with channel/thread management permissions;
- asks for explicit modal confirmation by typing `close` or `закрыть`;
- sets the ticket status to `closed`;
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

The `@everyone` role is rejected as a support role.
