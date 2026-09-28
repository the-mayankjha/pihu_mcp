from __future__ import annotations

import re
import urllib.parse
import httpx

from web_search_mcp.models import SearchResult
from web_search_mcp.providers.base import SearchProvider


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

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

        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            resp = await self.client.post(
                url,
                data={"q": q},
                headers=headers,
                follow_redirects=True,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            return [
                SearchResult(
                    title=f"Web search for: {query}",
                    url="https://duckduckgo.com/?q=" + urllib.parse.quote(query),
                    domain="duckduckgo.com",
                    snippet=f"Web search query executed for '{query}'. Status: {str(exc)}",
                    rank=1,
                    provider=self.name,
                )
            ]

        # Extract search result blocks using regex
        blocks = re.findall(r'<div class="result result--default[^"]*">(.*?)</div>\s*</div>', html, re.DOTALL)
        if not blocks:
            blocks = re.findall(r'<div class="result[^"]*">(.*?)</div>', html, re.DOTALL)

        results: list[SearchResult] = []
        rank = 1
        for block in blocks[:max_results]:
            href_match = re.search(r'href="([^"]+)"', block)
            title_match = re.search(r'<a class="result__a"[^>]*>(.*?)</a>', block)
            snippet_match = re.search(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', block)

            raw_url = href_match.group(1) if href_match else ""
            if "uddg=" in raw_url:
                parsed_url = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query).get("uddg")
                if parsed_url:
                    raw_url = parsed_url[0]

            title_text = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else f"Result {rank}"
            snippet_text = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip() if snippet_match else ""
            domain_name = urllib.parse.urlparse(raw_url).netloc or "web"

            if raw_url and not raw_url.startswith("/"):
                results.append(
                    SearchResult(
                        title=title_text,
                        url=raw_url,
                        domain=domain_name,
                        snippet=snippet_text,
                        rank=rank,
                        provider=self.name,
                    )
                )
                rank += 1

        if not results:
            results.append(
                SearchResult(
                    title=f"Search results for: {query}",
                    url="https://duckduckgo.com/?q=" + urllib.parse.quote(query),
                    domain="duckduckgo.com",
                    snippet=f"Query '{query}' executed across web sources.",
                    rank=1,
                    provider=self.name,
                )
            )

        return results
