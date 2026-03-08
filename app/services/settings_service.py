"""Settings service — cached access to AppConfig key-value store."""
from __future__ import annotations

from app.database import get_session
from app.models.user import AppConfig

_cache: dict[str, str] = {}


def get_config(key: str, default: str = "") -> str:
    if key in _cache:
        return _cache[key]
    with get_session() as s:
        row = s.get(AppConfig, key)
        value = row.value if row else default
    _cache[key] = value
    return value


def set_config(key: str, value: str) -> None:
    _cache[key] = value
    with get_session() as s:
        row = s.get(AppConfig, key)
        if row:
            row.value = value
        else:
            s.add(AppConfig(key=key, value=value))


def invalidate_cache() -> None:
    _cache.clear()
