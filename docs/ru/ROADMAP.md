# Roadmap

**Язык:** [English](../en/ROADMAP.md) | Русский

Этапный roadmap приостановлен, пока выполняется операционная и документационная
чистка.

## Готово

1. Project scaffold, config, dependencies, Docker, README.
2. SQLAlchemy models, Alembic, repositories и DB startup check.
3. Slash-команды: `/tickets-setup`, `/tickets-status`, `/tickets-reset`.
4. Embed панели поддержки и persistent buttons.
5. Модалка создания тикета, приватные пользовательские каналы и threads.
6. Закрытие тикета и logging.
7. Полировка списка "My tickets".
8. Панель настроек и выбор роли поддержки.
9. Edge cases, permission hardening и error handling.
10. Разделение документации и закрытая лицензия.
11. Runtime-скрипты для локального запуска и Ubuntu 24.04.

## Текущее Направление

Идея web-admin намеренно удалена как избыточная для текущего scope. Ближайшая работа
должна оставаться вокруг Discord-бота, operations и будущей мультиязычности внутри
самого бота.
