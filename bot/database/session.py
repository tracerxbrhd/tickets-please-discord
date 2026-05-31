"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

LOGGER = logging.getLogger(__name__)


class Database:
    """Owns the async engine and session factory for the bot process."""

    def __init__(self, database_url: str, *, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Open a transactional async session."""

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def check_connection(self) -> None:
        """Verify that the configured database is reachable."""

        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def wait_until_ready(
        self,
        *,
        attempts: int = 12,
        delay_seconds: float = 5.0,
    ) -> None:
        """Wait until the configured database accepts connections."""

        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                await self.check_connection()
                return
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                LOGGER.warning(
                    "Database is not ready yet (%s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                await asyncio.sleep(delay_seconds)

        raise RuntimeError(
            f"Database is not ready after {attempts} attempts"
        ) from last_error

    async def dispose(self) -> None:
        """Close pooled database connections."""

        await self.engine.dispose()
