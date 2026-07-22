from datetime import datetime, timedelta, timezone
from typing import Any


CACHE_TTL_MINUTES = 60

_cache: dict[str, dict[str, Any]] = {}


def get_cache(h3_index: str):
    item = _cache.get(h3_index)

    if not item:
        return None

    expires_at = item.get("expires_at")

    if expires_at and datetime.now(timezone.utc) > expires_at:
        _cache.pop(h3_index, None)
        return None

    return item.get("data")


def set_cache(
    h3_index: str,
    data: dict,
    ttl_minutes: int = CACHE_TTL_MINUTES,
):
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=ttl_minutes)
    )

    _cache[h3_index] = {
        "data": data,
        "expires_at": expires_at,
    }


def clear_cache():
    _cache.clear()
