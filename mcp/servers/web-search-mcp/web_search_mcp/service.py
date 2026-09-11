from __future__ import annotations

import asyncio
import hashlib
import time

import httpx

from web_search_mcp.cache import TTLCache
from web_search_mcp.config import Settings
from web_search_mcp.fetcher import Fetcher
from web_search_mcp.models import Evidence, ResearchResponse, SearchResponse
from web_search_mcp.providers.brave import BraveProvider


class WebService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.fetch_timeout, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self.search_cache = TTLCache[SearchResponse](settings.cache_ttl)
        self.fetcher = Fetcher(self.client, settings)
        self.providers = {
            "brave": BraveProvider(settings.brave_api_key, self.client),
        }

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _key(*parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    async def search(
        self,
        query: str,
        *,
        max_results: int = 8,
        freshness: str | None = None,
        domain: str | None = None,
    ) -> SearchResponse:
        key = self._key(query, str(max_results), freshness or "", domain or "")
        cached = self.search_cache.get(key)
        if cached:
            return cached.model_copy(update={"cached": True})

        started = time.perf_counter()
        provider_name = self.settings.search_provider
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown search provider: {provider_name}")

        results = await provider.search(
            query,
            max_results=min(max_results, self.settings.max_results),
            freshness=freshness,
            domain=domain,
        )

        response = SearchResponse(
            query=query,
            results=results,
            provider=provider_name,
            took_ms=round((time.perf_counter() - started) * 1000),
        )
        self.search_cache.set(key, response)
        return response

    async def search_and_read(
        self,
        query: str,
        *,
        max_results: int = 5,
        max_chars_per_source: int = 8000,
    ) -> ResearchResponse:
        started = time.perf_counter()
        search = await self.search(query, max_results=max_results)

        pages = await asyncio.gather(
            *(self.fetcher.fetch(item.url, max_chars=max_chars_per_source) for item in search.results),
            return_exceptions=True,
        )

        evidence: list[Evidence] = []
        for item, page in zip(search.results, pages):
            if isinstance(page, Exception):
                continue
            evidence.append(
                Evidence(
                    title=item.title,
                    url=page.final_url,
                    domain=item.domain,
                    snippet=item.snippet,
                    content=page.text,
                    rank=item.rank,
                    provider=item.provider,
                )
            )

        return ResearchResponse(
            query=query,
            sources=evidence,
            took_ms=round((time.perf_counter() - started) * 1000),
        )
