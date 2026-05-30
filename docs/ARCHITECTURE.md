# Architecture

## Stack

- Python 3.12+
- hikari
- hikari-lightbulb
- hikari-miru
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Docker and Docker Compose
- pydantic-settings

## Package Layout

```text
bot/
├── main.py              # application entrypoint and bot factory
├── config.py            # environment-driven settings
├── logging.py           # process logging setup
├── runtime.py           # dependencies shared by Lightbulb extensions
├── database/            # SQLAlchemy models, async sessions, Alembic, repositories
├── extensions/          # slash commands and event extensions
├── services/            # business logic independent from Discord adapters
├── ui/                  # embeds, views, modals, selects
└── utils/               # shared helpers and domain exceptions

web/
├── main.py              # FastAPI app factory and uvicorn entrypoint
├── security.py          # bearer-token admin auth
├── schemas.py           # response models
└── admin_service.py     # read-only dashboard read models
```

Discord adapters live in `extensions/` and `ui/`. Business behavior lives in
`services/`, with data access kept behind repository helpers in `database/`.

The web admin package reuses database repositories without depending on hikari command
handlers.

## Database

The initial PostgreSQL schema is managed through Alembic:

- `guild_settings`: per-server channel/message IDs and enabled state.
- `support_roles`: support role IDs per server.
- `user_ticket_channels`: one private ticket channel per user per server.
- `tickets`: ticket records with `open`, `in_progress`, `waiting_user`,
  `waiting_staff`, and `closed` statuses.
- `ticket_attachments`: metadata for user-provided attachments.
- `ticket_events`: append-only ticket history with structured JSON payloads.

The bot checks database connectivity during startup and disposes the async engine on
shutdown. Applying migrations remains an explicit operational command.
