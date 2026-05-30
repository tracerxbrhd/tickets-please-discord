# Операции

**Язык:** [English](../en/OPERATIONS.md) | Русский

## Конфигурация

Скопируйте пример окружения и заполните Discord token:

```bash
cp .env.example .env
```

Переменные:

- `DISCORD_TOKEN`: токен Discord-бота.
- `DATABASE_URL`: async SQLAlchemy PostgreSQL URL.
- `DEV_GUILD_IDS`: необязательные ID guild через запятую для dev-команд.
- `ENVIRONMENT`: `local`, `development`, `staging` или `production`.
- `LOG_LEVEL`: уровень Python logging, например `INFO` или `DEBUG`.

## Runtime-Скрипты

Основные operational entrypoints находятся в `scripts/`.

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

Установка Docker и Compose plugin на чистый Ubuntu 24.04:

```bash
sudo bash scripts/ubuntu-install-docker.sh
```

## Ручные Docker-Команды

```bash
docker compose --profile tools run --rm migrate
docker compose up --build
```

Команда migrate применяет текущую Alembic-схему к PostgreSQL. Compose stack затем
запускает PostgreSQL и бота.

## Локальный Python-Запуск

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
alembic upgrade head
python -m bot.main
```

Для локального запуска вне Docker используйте локальный database URL:

```env
DATABASE_URL=postgresql+asyncpg://tickets:tickets@localhost:5432/tickets
```

## Команды Скриптов

- `check`: проверяет Docker, Compose и состояние `.env`.
- `init-env`: создаёт `.env` из `.env.example`, если файла нет.
- `build`: собирает Docker images.
- `start`: запускает `db`, применяет migrations, затем запускает `bot`.
- `stop`: останавливает и удаляет compose containers.
- `restart`: перезапускает `bot`.
- `rebuild`: собирает, применяет migrations и пересоздаёт `bot`.
- `status`: показывает `docker compose ps`.
- `logs [service] [tail]`: показывает logs для `bot` или одного сервиса.
- `migrate`: запускает Alembic migrations.
- `db`: запускает только PostgreSQL.
- `bot`: запускает только бота после database и migrations.
- `backup-db`: пишет PostgreSQL custom-format dump в `./backups`.

## Требуемые Discord-Права

Боту нужны права:

- использовать application commands;
- создавать каналы и управлять ими;
- создавать threads и управлять ими;
- отправлять сообщения и embeds;
- читать message history;
- управлять permission overwrites.

`/tickets-setup`, `/tickets-status` и `/tickets-reset` требуют право `Manage Server`
у пользователя, который вызывает команду.
