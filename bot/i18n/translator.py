"""Small JSON-backed localization layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

DEFAULT_LOCALE = "en"


@dataclass(frozen=True, slots=True)
class Language:
    """Language metadata shown in settings controls."""

    code: str
    name: str
    native_name: str


def normalize_locale(locale: str | None) -> str:
    """Return a supported locale code, falling back to English."""

    if locale is None:
        return DEFAULT_LOCALE

    normalized = locale.strip().casefold()
    if normalized in _load_catalogs():
        return normalized
    return DEFAULT_LOCALE


def available_languages() -> list[Language]:
    """Return languages discovered from bundled locale files."""

    languages: list[Language] = []
    for code, catalog in sorted(_load_catalogs().items()):
        meta = catalog.get("_meta", {})
        languages.append(
            Language(
                code=code,
                name=str(meta.get("name", code)),
                native_name=str(meta.get("native_name", meta.get("name", code))),
            )
        )
    return languages


def t(locale: str | None, key: str, **values: object) -> str:
    """Translate a dotted key and format placeholders."""

    catalog = _load_catalogs()[normalize_locale(locale)]
    fallback_catalog = _load_catalogs()[DEFAULT_LOCALE]
    value = _lookup(catalog, key)
    if value is None:
        value = _lookup(fallback_catalog, key)
    if value is None:
        return key
    if not isinstance(value, str):
        return key
    return value.format(**values)


def _lookup(catalog: dict[str, Any], key: str) -> Any:
    current: Any = catalog
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


@lru_cache(maxsize=1)
def _load_catalogs() -> dict[str, dict[str, Any]]:
    catalogs: dict[str, dict[str, Any]] = {}
    locale_root = resources.files("bot.i18n.locales")
    for locale_file in locale_root.iterdir():
        if locale_file.suffix != ".json":
            continue
        with locale_file.open("r", encoding="utf-8") as file:
            catalogs[locale_file.stem] = json.load(file)

    if DEFAULT_LOCALE not in catalogs:
        raise RuntimeError(f"Missing default locale: {DEFAULT_LOCALE}")
    return catalogs
