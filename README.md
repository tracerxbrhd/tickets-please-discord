![Tickets! Please banner](./assets/banner.png)

<p align="center">
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/ci.yml"><img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/docker-build.yml"><img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/docker-build.yml/badge.svg" alt="Docker Build"></a>
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/migration-check.yml"><img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/migration-check.yml/badge.svg" alt="Migration Check"></a>
  <a href="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/codeql.yml"><img src="https://github.com/tracerxbrhd/tickets-please-discord/actions/workflows/codeql.yml/badge.svg" alt="CodeQL"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Discord-Bot-5865F2?style=flat-square&logo=discord&logoColor=white" alt="Discord Bot">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/License-Proprietary-purple?style=flat-square" alt="Proprietary License">
</p>

<p align="center">
  <a href="https://top.gg/bot/1510222334814982254"><img src="https://top.gg/api/widget/servers/1510222334814982254.svg"></a>
  <a href="https://top.gg/bot/1510222334814982254"><img src="https://top.gg/api/widget/upvotes/1510222334814982254.svg"></a>
  <a href="https://top.gg/bot/1510222334814982254"><img src="https://top.gg/api/widget/owner/1510222334814982254.svg"></a>
</p>

# Tickets! Please

**Language:** English | [Русский](README.ru.md)

Tickets! Please is a proprietary Discord support ticket bot for servers that need
a structured support workflow.

The repository language and the product language are English. Bot UI localization
will be handled later; the current repository documentation is available in English
and Russian.

## Features

- `/tickets-setup`, `/tickets-status`, and `/tickets-reset` slash commands.
- Persistent support panel with ticket creation and "my tickets" actions.
- Ticket creation modal with private user channels and per-ticket threads.
- Ticket closure flow with confirmation, audit event, and thread archival.
- Settings panel role selector for the support role.
- Flexible server language selection with English and Russian bundled.
- PostgreSQL persistence for settings, roles, channels, tickets, attachments, and events.
- Operational scripts for Windows/PowerShell and Ubuntu 24.04.

## Documentation

- [Documentation index](docs/README.md)
- [Bot behavior](docs/en/BOT.md)
- [Architecture](docs/en/ARCHITECTURE.md)
- [Operations](docs/en/OPERATIONS.md)
- [Roadmap](docs/en/ROADMAP.md)
- [Runtime scripts](scripts/README.md)

## License

This project is proprietary and all rights are reserved. No project file may be used,
copied, modified, distributed, hosted, deployed, or reused without prior written
permission from the copyright holder. See [LICENSE](LICENSE).
