# Runtime-Скрипты

**Язык:** [English](README.md) | Русский

Этапный roadmap приостановлен. Эти скрипты помогают запускать проект локально и на
Ubuntu 24.04.

## Локально На Windows

Запускайте PowerShell из корня проекта:

```powershell
./scripts/local.ps1 init-env
./scripts/local.ps1 start
./scripts/local.ps1 logs bot 200
./scripts/local.ps1 stop
```

## Сервер Ubuntu 24.04

Установить Docker на чистом сервере:

```bash
sudo bash scripts/ubuntu-install-docker.sh
```

После добавления пользователя в группу `docker` выйдите из сессии и зайдите снова.
Затем:

```bash
bash scripts/server.sh init-env
bash scripts/server.sh start
bash scripts/server.sh logs bot 200
bash scripts/server.sh stop
```

## Команды

- `check`: проверяет Docker, Compose и `.env`.
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

Оба dispatchers блокируют startup, если `.env` всё ещё содержит placeholder
`replace-with`. Контейнер бота также выполняет `alembic upgrade head` перед
открытием Discord gateway, поэтому прямой деплой через Docker Compose тоже
применяет обязательные миграции базы данных.
