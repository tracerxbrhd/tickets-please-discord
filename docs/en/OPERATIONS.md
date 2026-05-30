# Operations

**Language:** English | [Русский](../ru/OPERATIONS.md)

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

## Runtime Scripts

The preferred operational entrypoints are in `scripts/`.

Windows/PowerShell:

```powershell
./scripts/local.ps1 start
./scripts/local.ps1 logs bot 200
./scripts/local.ps1 stop
```

Ubuntu 24.04:

```bash
bash scripts/server.sh start
bash scripts/server.sh logs bot 200
bash scripts/server.sh stop
```

Install Docker and the Compose plugin on a fresh Ubuntu 24.04 host:

```bash
sudo bash scripts/ubuntu-install-docker.sh
```

## Manual Docker Commands

```bash
docker compose --profile tools run --rm migrate
docker compose up --build
```

The migration command applies the current Alembic schema to PostgreSQL. The Compose
stack then starts PostgreSQL and the bot.

## Local Python Run

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

## Script Commands

- `check`: validate Docker, Compose, and `.env` state.
- `init-env`: create `.env` from `.env.example` when missing.
- `build`: build all Docker images.
- `start`: start `db`, run migrations, then start `bot`.
- `stop`: stop and remove compose containers.
- `restart`: restart `bot`.
- `rebuild`: build, migrate, and recreate `bot`.
- `status`: show `docker compose ps`.
- `logs [service] [tail]`: follow logs for `bot` or one service.
- `migrate`: run Alembic migrations.
- `db`: start only PostgreSQL.
- `bot`: start only the bot after database and migrations.
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
