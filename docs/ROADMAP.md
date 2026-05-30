# Development Stages

1. Project scaffold, config, dependencies, Docker, README. Done.
2. SQLAlchemy models, Alembic, repositories, and DB startup check. Done.
3. Slash commands: `/tickets-setup`, `/tickets-status`, `/tickets-reset`. Done.
4. Support panel embed and persistent buttons. Done.
5. Ticket creation modal, private user channels, and per-ticket threads. Done.
6. Ticket closure flow and logging. Done.
7. "My tickets" listing polish. Done.
8. Settings panel and support role selection. Done.
9. Edge cases, permission hardening, and error handling. Done.
10. Documentation split, closed license, and web-admin expansion notes. Done.
11. Read-only web-admin API scaffold. Done.

## Current Project State

The bot has a working Discord-first ticket flow:

- setup/status/reset slash commands;
- persistent support and settings panels;
- ticket creation and closure flows;
- PostgreSQL persistence;
- support-role permission propagation;
- operational hardening for stale Discord resources.
- a token-protected read-only admin API for configured guilds and recent tickets.

The next product direction is a browser dashboard UI over the web-admin API.
