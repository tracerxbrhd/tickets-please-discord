#!/usr/bin/env bash
set -Eeuo pipefail

COMMAND="${1:-help}"
SERVICE="${2:-}"
TAIL="${3:-120}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/server.sh <command> [service] [tail]

Commands:
  help        Show this help.
  check       Check Docker, Compose, and .env state.
  init-env    Create .env from .env.example when .env is missing.
  build       Build Docker images.
  start       Start db, run migrations, then start bot.
  stop        Stop and remove compose containers.
  restart     Restart bot container.
  rebuild     Build images, run migrations, recreate bot.
  status      Show compose container status.
  logs        Follow bot logs, or one service when provided.
  migrate     Run Alembic migrations.
  db          Start only PostgreSQL.
  bot         Start db, run migrations, then start only the bot.
  backup-db   Create a PostgreSQL custom-format dump in ./backups.

Examples:
  bash scripts/server.sh start
  bash scripts/server.sh logs bot 200
  bash scripts/server.sh rebuild
EOF
}

compose() {
  docker compose "$@"
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI was not found. Install Docker Engine first." >&2
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is not available." >&2
    exit 1
  fi
}

init_env() {
  if [[ -f .env ]]; then
    echo ".env already exists."
    return
  fi

  cp .env.example .env
  echo "Created .env from .env.example. Fill secrets before starting services."
}

require_env() {
  if [[ ! -f .env ]]; then
    init_env
    echo "Fill .env and run the command again." >&2
    exit 1
  fi

  if grep -q "replace-with" .env; then
    echo ".env still contains placeholder values." >&2
    exit 1
  fi
}

start_db() {
  compose up -d db
}

run_migrations() {
  compose --profile tools run --rm migrate
}

backup_db() {
  local stamp
  local backup_path

  stamp="$(date +%Y%m%d-%H%M%S)"
  mkdir -p backups
  backup_path="backups/tickets-${stamp}.dump"

  compose exec -T db pg_dump -U tickets -Fc -f /tmp/tickets.dump tickets
  compose cp db:/tmp/tickets.dump "$backup_path"
  compose exec -T db rm -f /tmp/tickets.dump
  echo "Database backup written to $backup_path"
}

case "$COMMAND" in
  help)
    usage
    ;;
  check)
    require_docker
    if [[ -f .env ]]; then
      echo ".env exists."
    else
      echo ".env is missing. Run: bash scripts/server.sh init-env"
    fi
    compose ps
    ;;
  init-env)
    init_env
    ;;
  build)
    require_docker
    compose build
    ;;
  start)
    require_docker
    require_env
    start_db
    run_migrations
    compose up -d bot
    ;;
  stop)
    require_docker
    compose down
    ;;
  restart)
    require_docker
    require_env
    compose restart bot
    ;;
  rebuild)
    require_docker
    require_env
    compose build
    start_db
    run_migrations
    compose up -d --force-recreate bot
    ;;
  status)
    require_docker
    compose ps
    ;;
  logs)
    require_docker
    if [[ -n "$SERVICE" ]]; then
      compose logs --tail "$TAIL" -f "$SERVICE"
    else
      compose logs --tail "$TAIL" -f bot
    fi
    ;;
  migrate)
    require_docker
    require_env
    start_db
    run_migrations
    ;;
  db)
    require_docker
    start_db
    ;;
  bot)
    require_docker
    require_env
    start_db
    run_migrations
    compose up -d bot
    ;;
  backup-db)
    require_docker
    require_env
    start_db
    backup_db
    ;;
  *)
    usage
    echo "Unknown command: $COMMAND" >&2
    exit 1
    ;;
esac
