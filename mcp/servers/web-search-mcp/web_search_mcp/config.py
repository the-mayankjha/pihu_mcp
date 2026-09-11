from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    brave_api_key: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
    search_provider: str = os.getenv("WEB_SEARCH_PROVIDER", "brave")
    max_results: int = _int("WEB_SEARCH_MAX_RESULTS", 8)
    fetch_timeout: float = float(os.getenv("WEB_FETCH_TIMEOUT", "12"))
    max_bytes: int = _int("WEB_FETCH_MAX_BYTES", 5_000_000)
    max_chars: int = _int("WEB_FETCH_MAX_CHARS", 30_000)
    max_redirects: int = _int("WEB_MAX_REDIRECTS", 5)
    cache_ttl: int = _int("WEB_CACHE_TTL_SECONDS", 300)


settings = Settings()
