from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    expires: float
    value: T


class TTLCache(Generic[T]):
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._items: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._items.get(key)
        if not entry:
            return None
        if entry.expires <= time.monotonic():
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._items[key] = _Entry(time.monotonic() + self.ttl, value)
