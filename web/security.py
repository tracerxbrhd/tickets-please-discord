"""Authentication helpers for the web admin API."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from bot.config import Settings


async def require_admin_token(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Require a bearer token matching WEB_ADMIN_TOKEN."""

    settings: Settings = request.app.state.settings
    configured_token = settings.web_admin_token
    if configured_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WEB_ADMIN_TOKEN is not configured.",
        )

    expected_token = configured_token.get_secret_value()
    provided_token = _parse_bearer_token(authorization)
    if provided_token is None or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _parse_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not token.strip():
        return None
    return token.strip()
