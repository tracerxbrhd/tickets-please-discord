![Tickets! Please banner](./assets/banner.png)

<p align="center">
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/ci.yml">
    <img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/docker-build.yml">
    <img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/docker-build.yml/badge.svg" alt="Docker Build">
  </a>
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/migration-check.yml">
    <img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/migration-check.yml/badge.svg" alt="Migration Check">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Discord-Bot-5865F2?style=flat-square&logo=discord&logoColor=white" alt="Discord Bot">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/License-Proprietary-purple?style=flat-square" alt="Proprietary License">
</p>

<a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/codeql.yml">
  <img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/codeql.yml/badge.svg" alt="CodeQL">
</a>

# Tickets! Please

**Язык:** [English](README.md) | Русский

Tickets! Please - закрытый Discord-бот для серверов, которым нужен структурированный
процесс обращений в поддержку.

Основной язык репозитория и продукта - английский. Локализацию интерфейса самого
бота добавим позже; документация репозитория уже доступна на английском и русском.

## Возможности

- Slash-команды `/tickets-setup`, `/tickets-status` и `/tickets-reset`.
- Постоянная панель поддержки с созданием тикета и действием "мои тикеты".
- Модалка создания тикета, приватные пользовательские каналы и отдельные threads.
- Закрытие тикета с подтверждением, audit-событием и архивированием thread.
- Панель настроек с выбором роли поддержки.
- PostgreSQL для настроек, ролей, каналов, тикетов, вложений и событий.
- Операционные скрипты для Windows/PowerShell и Ubuntu 24.04.

## Документация

- [Индекс документации](docs/README.md)
- [Поведение бота](docs/ru/BOT.md)
- [Архитектура](docs/ru/ARCHITECTURE.md)
- [Операции](docs/ru/OPERATIONS.md)
- [Roadmap](docs/ru/ROADMAP.md)
- [Runtime-скрипты](scripts/README.ru.md)

## Лицензия

Проект является proprietary, все права защищены. Нельзя использовать, копировать,
изменять, распространять, хостить, деплоить или переиспользовать файлы проекта без
предварительного письменного разрешения правообладателя. См. [LICENSE](LICENSE).
