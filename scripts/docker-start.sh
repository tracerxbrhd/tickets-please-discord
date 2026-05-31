#!/usr/bin/env sh
set -eu

attempt=1
max_attempts=12

until alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Database migrations failed after $max_attempts attempts." >&2
    exit 1
  fi

  echo "Database is not ready for migrations yet ($attempt/$max_attempts)." >&2
  attempt=$((attempt + 1))
  sleep 5
done

exec python -m bot.main
