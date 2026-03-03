"""In-memory TTL cache for GenAI results.

Keys are SHA-256 hashes of normalised (description, price, category, subcategory).
Entries expire after GENAI_CACHE_TTL seconds (default 300).

This is a process-local cache.  In a multi-worker setup (e.g. Gunicorn with
4 workers) each worker has its own cache — acceptable trade-off given the
latency cost of GenAI calls.
"""
import hashlib
import logging
import os
import time
from typing import Any

log = logging.getLogger(__name__)

# { key: (value, expire_monotonic_ts) }
_cache: dict[str, tuple[Any, float]] = {}


def _default_ttl() -> int:
    return int(os.environ.get("GENAI_CACHE_TTL", "300"))


def _make_key(*parts: str) -> str:
    normalised = "|".join(str(p).lower().strip() for p in parts)
    return hashlib.sha256(normalised.encode()).hexdigest()


def make_analysis_key(
    description: str,
    price: str,
    category: str,
    subcategory: str = "",
) -> str:
    """Canonical cache key for an analysis request."""
    return _make_key(description, price, category, subcategory)


def cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expire_ts = entry
    if time.monotonic() > expire_ts:
        del _cache[key]
        log.debug("Cache miss (expired) key=%s…", key[:8])
        return None
    log.debug("Cache hit key=%s…", key[:8])
    return value


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    if ttl is None:
        ttl = _default_ttl()
    _cache[key] = (value, time.monotonic() + ttl)
    log.debug("Cache set key=%s… ttl=%ds", key[:8], ttl)


def cache_clear() -> None:
    """Flush entire cache — useful for tests."""
    _cache.clear()
