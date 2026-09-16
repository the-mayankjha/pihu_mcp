from __future__ import annotations

from abc import ABC, abstractmethod
from web_search_mcp.models import SearchResult


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int,
        freshness: str | None = None,
        domain: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError
