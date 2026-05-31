# Runtime Scripts

**Language:** English | [Русский](README.ru.md)

The stage roadmap is paused. These scripts are operational helpers for local
development and Ubuntu 24.04 deployment.

## Local Windows

Use PowerShell from the project root:

```powershell
./scripts/local.ps1 init-env
./scripts/local.ps1 start
./scripts/local.ps1 logs bot 200
./scripts/local.ps1 stop
```

## Ubuntu 24.04 Server

Install Docker on a fresh server:

```bash
sudo bash scripts/ubuntu-install-docker.sh
```

Log out and back in after the installer adds your user to the `docker` group. Then:

```bash
bash scripts/server.sh init-env
bash scripts/server.sh start
bash scripts/server.sh logs bot 200
bash scripts/server.sh stop
```

## Commands

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

Both dispatchers block startup when `.env` still contains `replace-with`
placeholders. The bot container also runs `alembic upgrade head` before opening
the Discord gateway, so direct Docker Compose deploys still apply required
database migrations.
