![bot-banner](./assets/tickets-please-banner.png)

# Tickets! Please

Tickets! Please is a private Discord support ticket bot for servers that need a
structured support workflow.

The bot creates a support panel, private user ticket channels, per-ticket threads,
a settings panel for support roles, and a logs channel for operational events.

## Current Features

- `/tickets-setup`, `/tickets-status`, and `/tickets-reset` slash commands.
- Persistent support panel with ticket creation and "my tickets" actions.
- Ticket creation modal with per-user private channels and per-ticket threads.
- Ticket closure flow with confirmation, audit event, and thread archival.
- Settings panel role selector for the support role.
- PostgreSQL persistence for settings, roles, channels, tickets, attachments, and events.
- Defensive handling for stale panels, missing channels, missing log access, and open
  ticket limits.

## Documentation

Detailed documentation lives outside the README:

- [Bot behavior](docs/BOT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Operations](docs/OPERATIONS.md)
- [Roadmap](docs/ROADMAP.md)
- [Web admin expansion notes](docs/WEB_ADMIN_EXPANSION.md)

## License

This project is proprietary and all rights are reserved. No project file may be used,
copied, modified, distributed, hosted, deployed, or reused without prior written
permission from the copyright holder. See [LICENSE](LICENSE).
