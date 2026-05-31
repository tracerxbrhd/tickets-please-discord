# Архитектура

**Язык:** [English](../en/ARCHITECTURE.md) | Русский

## Стек

- Python 3.12+
- hikari
- hikari-lightbulb
- hikari-miru
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Docker и Docker Compose
- pydantic-settings

## Структура Пакетов

```text
bot/
├── main.py              # точка входа и bot factory
├── config.py            # настройки из окружения
├── logging.py           # настройка process logging
├── runtime.py           # зависимости для Lightbulb extensions
├── database/            # SQLAlchemy models, sessions, Alembic, repositories
├── extensions/          # slash-команды и Discord event handlers
├── i18n/                # JSON-каталоги локалей и translation helpers
├── services/            # бизнес-логика вне Discord adapters
├── ui/                  # embeds, views, modals, selects
└── utils/               # общие helpers и domain exceptions
```

Discord adapters находятся в `extensions/` и `ui/`. Бизнес-поведение находится в
`services/`, а доступ к данным закрыт repository helpers в `database/`.

## База Данных

Схема PostgreSQL управляется через Alembic:

- `guild_settings`: ID каналов/сообщений сервера и флаг включения.
- `guild_settings.locale`: выбранный язык сервера, по умолчанию `en`.
- `support_roles`: ID ролей поддержки по серверам.
- `user_ticket_channels`: один приватный ticket-канал на пользователя сервера.
- `tickets`: записи тикетов со статусами `open`, `in_progress`, `waiting_user`,
  `waiting_staff` и `closed`.
- `ticket_attachments`: metadata пользовательских вложений.
- `ticket_events`: append-only история тикета со structured JSON payload.

Бот проверяет подключение к базе при старте и закрывает async engine при остановке.

## Локализация

Переводы находятся в `bot/i18n/locales/*.json`. Translation helper использует
английский fallback, если локаль или ключ отсутствует. Для добавления нового языка
нужно добавить JSON-каталог с `_meta.name`, `_meta.native_name` и теми же ключами.
