"""FastAPI entrypoint for the Tickets! Please web admin API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status

from bot.config import Settings, get_settings
from bot.database.session import Database
from bot.logging import configure_logging
from web.admin_service import AdminReadService
from web.schemas import GuildDetail, GuildSummary, HealthResponse
from web.security import require_admin_token


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the web admin API application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    database = Database(str(resolved_settings.database_url))
    admin_service = AdminReadService()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.database = database
        app.state.admin_service = admin_service
        await database.check_connection()
        try:
            yield
        finally:
            await database.dispose()

    app = FastAPI(
        title="Tickets! Please Admin API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        database: Database = request.app.state.database
        await database.check_connection()
        return HealthResponse(
            status="ok",
            database="ok",
            environment=resolved_settings.environment,
        )

    @app.get(
        "/admin/guilds",
        response_model=list[GuildSummary],
        dependencies=[Depends(require_admin_token)],
    )
    async def list_guilds(request: Request) -> list[GuildSummary]:
        database: Database = request.app.state.database
        service: AdminReadService = request.app.state.admin_service
        async with database.session() as session:
            return await service.list_guilds(session)

    @app.get(
        "/admin/guilds/{guild_id}",
        response_model=GuildDetail,
        dependencies=[Depends(require_admin_token)],
    )
    async def get_guild(request: Request, guild_id: int) -> GuildDetail:
        database: Database = request.app.state.database
        service: AdminReadService = request.app.state.admin_service
        async with database.session() as session:
            detail = await service.get_guild(session, guild_id=guild_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guild settings were not found.",
            )
        return detail

    return app


app = create_app()


def run() -> None:
    """Run the web admin API through uvicorn."""

    uvicorn.run("web.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
