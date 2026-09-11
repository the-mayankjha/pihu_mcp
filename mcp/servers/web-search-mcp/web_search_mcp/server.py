from __future__ import annotations

from mcp.server import MCPServer

from web_search_mcp.config import settings
from web_search_mcp.models import PageContent, ResearchResponse, SearchResponse
from web_search_mcp.service import WebService

mcp = MCPServer(
    "PIHU Web Search MCP",
    instructions=(
        "Fast, structured web search and retrieval for PIHU. "
        "Use web.search for discovery, web.fetch for a known URL, "
        "and web.search_and_read for multi-source evidence. "
        "Network access is online-only."
    ),
)

service = WebService(settings)


@mcp.tool()
async def web_search(
    query: str,
    max_results: int = 8,
    freshness: str | None = None,
    domain: str | None = None,
) -> SearchResponse:
    """Search the public web and return normalized, ranked search results."""
    if not query.strip():
        raise ValueError("query must not be empty")
    return await service.search(
        query.strip(),
        max_results=max_results,
        freshness=freshness,
        domain=domain,
    )


@mcp.tool()
async def web_fetch(
    url: str,
    max_chars: int = 30000,
) -> PageContent:
    """Safely fetch a public HTTP(S) webpage and extract readable content."""
    return await service.fetcher.fetch(url, max_chars=max_chars)


@mcp.tool()
async def web_search_and_read(
    query: str,
    max_results: int = 5,
    max_chars_per_source: int = 8000,
) -> ResearchResponse:
    """Search the web, fetch the top sources concurrently, and return evidence."""
    if not query.strip():
        raise ValueError("query must not be empty")
    return await service.search_and_read(
        query.strip(),
        max_results=max_results,
        max_chars_per_source=max_chars_per_source,
    )


@mcp.tool()
def web_capabilities() -> dict:
    """Return machine-readable capabilities for PIHU's capability registry."""
    return {
        "name": "web-search",
        "online": True,
        "network_required": True,
        "supports": ["search", "fetch", "search_and_read"],
        "browser_required": False,
        "max_results": settings.max_results,
    }


async def _shutdown() -> None:
    await service.close()


def main() -> None:
    # MCPServer owns the protocol lifecycle. Shutdown integration can be
    # wired into a lifespan when deploying as a long-lived HTTP service.
    mcp.run(transport="stdio")
