param(
    [string]$Command = "help",
    [string]$Service = "",
    [int]$Tail = 120
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Show-Help {
    @"
Usage:
  ./scripts/local.ps1 <command> [service] [tail]

Commands:
  help        Show this help.
  check       Check Docker, Compose, and .env state.
  init-env    Create .env from .env.example when .env is missing.
  build       Build Docker images.
  start       Start db, run migrations, then start bot and admin.
  stop        Stop and remove compose containers.
  restart     Restart bot and admin containers.
  rebuild     Build images, run migrations, recreate bot and admin.
  status      Show compose container status.
  logs        Follow bot and admin logs, or one service when provided.
  migrate     Run Alembic migrations.
  db          Start only PostgreSQL.
  bot         Start db, run migrations, then start only the bot.
  admin       Start db, run migrations, then start only the admin API.
  backup-db   Create a PostgreSQL custom-format dump in ./backups.

Examples:
  ./scripts/local.ps1 start
  ./scripts/local.ps1 logs bot 200
  ./scripts/local.ps1 rebuild
"@
}

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ComposeArgs)

    & docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Require-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI was not found. Install Docker Desktop first."
    }

    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose v2 is not available."
    }
}

function Initialize-Env {
    if (Test-Path ".env") {
        Write-Host ".env already exists."
        return
    }

    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Fill secrets before starting services."
}

function Require-Env {
    if (-not (Test-Path ".env")) {
        Initialize-Env
        throw "Fill .env and run the command again."
    }

    $envText = Get-Content ".env" -Raw
    if ($envText -match "replace-with") {
        throw ".env still contains placeholder values."
    }
}

function Start-Db {
    Invoke-Compose up -d db
}

function Invoke-Migrations {
    Invoke-Compose --profile tools run --rm migrate
}

function New-DatabaseBackup {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupDir = Join-Path $ProjectRoot "backups"
    $backupFile = "backups/tickets-$stamp.dump"
    $backupPath = Join-Path $ProjectRoot $backupFile

    New-Item -ItemType Directory -Force $backupDir *> $null
    Invoke-Compose exec -T db pg_dump -U tickets -Fc -f /tmp/tickets.dump tickets
    Invoke-Compose cp db:/tmp/tickets.dump $backupFile
    Invoke-Compose exec -T db rm -f /tmp/tickets.dump
    Write-Host "Database backup written to $backupPath"
}

$normalizedCommand = $Command.ToLowerInvariant()

switch ($normalizedCommand) {
    "help" {
        Show-Help
    }
    "check" {
        Require-Docker
        if (Test-Path ".env") {
            Write-Host ".env exists."
        } else {
            Write-Host ".env is missing. Run: ./scripts/local.ps1 init-env"
        }
        Invoke-Compose ps
    }
    "init-env" {
        Initialize-Env
    }
    "build" {
        Require-Docker
        Invoke-Compose build
    }
    "start" {
        Require-Docker
        Require-Env
        Start-Db
        Invoke-Migrations
        Invoke-Compose up -d bot admin
    }
    "stop" {
        Require-Docker
        Invoke-Compose down
    }
    "restart" {
        Require-Docker
        Require-Env
        Invoke-Compose restart bot admin
    }
    "rebuild" {
        Require-Docker
        Require-Env
        Invoke-Compose build
        Start-Db
        Invoke-Migrations
        Invoke-Compose up -d --force-recreate bot admin
    }
    "status" {
        Require-Docker
        Invoke-Compose ps
    }
    "logs" {
        Require-Docker
        if ($Service) {
            Invoke-Compose logs --tail $Tail -f $Service
        } else {
            Invoke-Compose logs --tail $Tail -f bot admin
        }
    }
    "migrate" {
        Require-Docker
        Require-Env
        Start-Db
        Invoke-Migrations
    }
    "db" {
        Require-Docker
        Start-Db
    }
    "bot" {
        Require-Docker
        Require-Env
        Start-Db
        Invoke-Migrations
        Invoke-Compose up -d bot
    }
    "admin" {
        Require-Docker
        Require-Env
        Start-Db
        Invoke-Migrations
        Invoke-Compose up -d admin
    }
    "backup-db" {
        Require-Docker
        Require-Env
        Start-Db
        New-DatabaseBackup
    }
    default {
        Show-Help
        throw "Unknown command: $Command"
    }
}
