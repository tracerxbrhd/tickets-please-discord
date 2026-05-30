# Web Admin API

Stage 11 adds the first separate web-admin surface. It is a token-protected,
read-only FastAPI API that exposes configured guilds and ticket dashboard data from
PostgreSQL.

## Security

Admin endpoints require:

```http
Authorization: Bearer <WEB_ADMIN_TOKEN>
```

If `WEB_ADMIN_TOKEN` is missing, admin endpoints return `503`. The `/health`
endpoint is intentionally unauthenticated and exposes only service status.

## Endpoints

- `GET /health`: process and database health.
- `GET /admin/guilds`: configured guilds, support role IDs, and ticket counts.
- `GET /admin/guilds/{guild_id}`: one guild, ticket counts, support role IDs, and
  the 20 most recent tickets.

The API is read-only. It does not mutate Discord resources or database settings.

## Run With Docker

```bash
docker compose up --build admin
```

The admin API listens on `http://localhost:8000` by default.

## Run Locally

```bash
uvicorn web.main:app --reload --host 127.0.0.1 --port 8000
```

Local execution needs the same `.env` file as the bot, plus `WEB_ADMIN_TOKEN`.

## Reusable Boundaries

- `bot.database`: SQLAlchemy models, async sessions, migrations, and repositories.
- `bot.services`: setup, settings, tickets, permissions, and logging behavior.
- `bot.config`: shared environment-driven settings.
- `web`: FastAPI application, auth guard, response schemas, and admin read models.

The web app reuses repositories and avoids importing `bot.ui` or `bot.extensions`,
because those modules are Discord interaction adapters.

## Next Candidate Admin Features

- Browser dashboard UI over the current read-only API.
- Update support roles from a web form.
- Inspect ticket event history from `ticket_events`.
- Surface permission drift warnings for missing channels, stale messages, or failed
  overwrite updates.
- Add operational controls for enabling or disabling the ticket system.
