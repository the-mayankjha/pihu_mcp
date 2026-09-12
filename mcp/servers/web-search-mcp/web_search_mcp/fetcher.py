from __future__ import annotations

import time
from urllib.parse import urljoin

import httpx
try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from web_search_mcp.config import Settings
from web_search_mcp.models import PageContent, PageMetadata
from web_search_mcp.security import UnsafeURL, validate_and_resolve


class Fetcher:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client = client
        self.settings = settings

    async def fetch(self, url: str, *, max_chars: int | None = None) -> PageContent:
        import re
        started = time.perf_counter()
        current = await validate_and_resolve(url)

        for _ in range(self.settings.max_redirects + 1):
            response = await self.client.get(
                current,
                follow_redirects=False,
                headers={
                    "User-Agent": "PIHU-WebMCP/0.1 (+https://github.com/pihu-ai)",
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
                },
            )

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise UnsafeURL("Redirect response has no Location header.")
                current = await validate_and_resolve(urljoin(current, location))
                continue

            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if not any(t in content_type for t in ("text/html", "application/xhtml+xml", "text/plain")):
                raise ValueError(f"Unsupported content type: {content_type}")

            raw = response.content
            if len(raw) > self.settings.max_bytes:
                raise ValueError("Response exceeds the configured size limit.")

            html = raw.decode(response.encoding or "utf-8", errors="replace")

            title = ""
            description = ""
            canonical_url = None

            if BeautifulSoup is not None:
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.get_text(" ", strip=True) if soup.title else ""
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    description = str(meta_desc.get("content", ""))
                canon = soup.find("link", rel="canonical")
                if canon:
                    canonical_url = canon.get("href")
            else:
                m_title = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                if m_title:
                    title = re.sub(r'<[^>]+>', '', m_title.group(1)).strip()

            text = ""
            if trafilatura is not None:
                text = trafilatura.extract(
                    html,
                    include_links=True,
                    include_tables=True,
                    favor_precision=True,
                ) or ""

            if not text:
                clean = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                lines = [line.strip() for line in clean.splitlines() if line.strip()]
                text = "\n".join(lines)

            limit = max_chars or self.settings.max_chars
            truncated = len(text) > limit
            if truncated:
                text = text[:limit]

            metadata = PageMetadata(
                title=title,
                description=description,
                canonical_url=(
                    soup.find("link", rel="canonical").get("href")
                    if soup.find("link", rel="canonical")
                    else None
                ),
            )

            return PageContent(
                url=url,
                final_url=current,
                status_code=response.status_code,
                content_type=content_type,
                title=title,
                text=text,
                metadata=metadata,
                truncated=truncated,
                took_ms=round((time.perf_counter() - started) * 1000),
            )

        raise UnsafeURL("Too many redirects.")
