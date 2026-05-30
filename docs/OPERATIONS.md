# Operations

## Configuration

Copy the example file and fill in the Discord token:

```bash
cp .env.example .env
```

Variables:

- `DISCORD_TOKEN`: Discord bot token.
- `DATABASE_URL`: async SQLAlchemy PostgreSQL URL.
- `DEV_GUILD_IDS`: optional comma-separated guild IDs for development command rollout.
- `ENVIRONMENT`: `local`, `development`, `staging`, or `production`.
- `LOG_LEVEL`: Python logging level, for example `INFO` or `DEBUG`.
- `WEB_ADMIN_TOKEN`: bearer token required by the web-admin API.

## Run With Docker

The preferred operational entrypoints are the scripts in `scripts/`.

On Windows/PowerShell:

```powershell
./scripts/local.ps1 start
./scripts/local.ps1 logs bot 200
./scripts/local.ps1 stop
```

On Ubuntu 24.04:

```bash
bash scripts/server.sh start
bash scripts/server.sh logs bot 200
bash scripts/server.sh stop
```

For a fresh Ubuntu 24.04 host, install Docker and the Compose plugin with:

```bash
sudo bash scripts/ubuntu-install-docker.sh
```

The manual Docker commands are:

```bash
docker compose --profile tools run --rm migrate
docker compose up --build
```

The migration command applies the current Alembic schema to PostgreSQL. The Compose
stack then starts PostgreSQL, the bot, and the web-admin API. The bot image uses
`python -m bot.main`; the admin service runs `uvicorn web.main:app`.

To run only the web-admin API after the database is healthy:

```bash
docker compose up --build admin
```

## Run Locally

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
alembic upgrade head
python -m bot.main
```

For local execution outside Docker, use a local database URL such as:

```env
DATABASE_URL=postgresql+asyncpg://tickets:tickets@localhost:5432/tickets
```

Run the web-admin API locally with:

```bash
uvicorn web.main:app --reload --host 127.0.0.1 --port 8000
```

Admin API requests need:

```http
Authorization: Bearer <WEB_ADMIN_TOKEN>
```

## Script Commands

- `check`: validate Docker, Compose, and `.env` state.
- `init-env`: create `.env` from `.env.example` when missing.
- `build`: build all Docker images.
- `start`: start `db`, run migrations, then start `bot` and `admin`.
- `stop`: stop and remove compose containers.
- `restart`: restart `bot` and `admin`.
- `rebuild`: build, migrate, and recreate `bot` and `admin`.
- `status`: show `docker compose ps`.
- `logs [service] [tail]`: follow logs for `bot admin` or one service.
- `migrate`: run Alembic migrations.
- `db`: start only PostgreSQL.
- `bot`: start only the bot after database and migrations.
- `admin`: start only the web-admin API after database and migrations.
- `backup-db`: write a PostgreSQL custom-format dump to `./backups`.

## Required Discord Permissions

The bot needs permissions to:

- use application commands;
- create and manage channels;
- create and manage threads;
- send messages and embeds;
- read message history;
- manage permission overwrites.

`/tickets-setup`, `/tickets-status`, and `/tickets-reset` require the invoking user
to have `Manage Server`.

## Hardening Behavior

The bot handles common operational drift defensively:

- stale support/settings panel messages are recreated by `/tickets-setup`;
- missing saved channels are recreated when setup runs again;
- missing or inaccessible per-user ticket channels are replaced on the next ticket
  creation for that user;
- failed log-channel writes do not fail the user-facing command or interaction;
- rejected permission overwrite updates are logged and do not roll back the saved
  support-role configuration.
