from __future__ import annotations

import httpx

from web_search_mcp.models import SearchResult
from web_search_mcp.providers.base import SearchProvider


class BraveProvider(SearchProvider):
    name = "brave"

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self.api_key = api_key
        self.client = client

    async def search(
        self,
        query: str,
        *,
        max_results: int,
        freshness: str | None = None,
        domain: str | None = None,
    ) -> list[SearchResult]:
        if not self.api_key:
            raise RuntimeError("BRAVE_SEARCH_API_KEY is not configured.")

        q = query
        if domain:
            q = f"site:{domain} {q}"

        params = {"q": q, "count": min(max_results, 20)}
        if freshness:
            params["freshness"] = freshness

        response = await self.client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params=params,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()

        output: list[SearchResult] = []
        for rank, item in enumerate(payload.get("web", {}).get("results", []), 1):
            output.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    domain=item.get("meta_url", {}).get("hostname", ""),
                    snippet=item.get("description", ""),
                    rank=rank,
                    provider=self.name,
                )
            )
        return output
