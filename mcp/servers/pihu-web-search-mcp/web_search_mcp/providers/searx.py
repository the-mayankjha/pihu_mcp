from __future__ import annotations

import urllib.parse
import httpx

from web_search_mcp.models import SearchResult
from web_search_mcp.providers.base import SearchProvider


class SearXProvider(SearchProvider):
    name = "searx"

    PUBLIC_INSTANCES = [
        "https://searx.be/search",
        "https://searx.space/search",
        "https://searx.prvcy.eu/search",
    ]

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
        q = query
        if domain:
            q = f"site:{domain} {q}"

        params = {"q": q, "format": "json"}
        for instance in self.PUBLIC_INSTANCES:
            try:
                resp = await self.client.get(
                    instance,
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                    timeout=8.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])
                    results: list[SearchResult] = []
                    for rank, item in enumerate(raw_results[:max_results], 1):
                        title = item.get("title", "")
                        url = item.get("url", "")
                        snippet = item.get("content", "")
                        domain_name = urllib.parse.urlparse(url).netloc or "web"
                        if url and title:
                            results.append(
                                SearchResult(
                                    title=title,
                                    url=url,
                                    domain=domain_name,
                                    snippet=snippet,
                                    rank=rank,
                                    provider=self.name,
                                )
                            )
                    if results:
                        return results
            except Exception:
                continue

        return []
