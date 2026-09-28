from mcp.server.fastmcp import FastMCP

from web_search_mcp.config import settings
from web_search_mcp.models import FileDownloadListResponse, FileDownloadResponse, PageContent, ResearchResponse, SearchResponse
from web_search_mcp.service import WebService

mcp = FastMCP(
    "pihu-web-search-mcp",
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
async def web_download_file(
    url: str,
    save_path: str | None = None,
) -> FileDownloadResponse:
    """Download a file (PDF, image, ZIP, dataset, code, binary) from any public URL into workspace."""
    if not url.strip():
        raise ValueError("url must not be empty")
    return await service.download_file(url.strip(), save_path=save_path)


@mcp.tool()
async def web_search_and_download(
    query: str,
    file_type: str = "pdf",
    max_files: int = 3,
    save_dir: str | None = None,
) -> FileDownloadListResponse:
    """Search the web for specific files (PDF, ZIP, CSV, etc.) and download matching files into workspace."""
    if not query.strip():
        raise ValueError("query must not be empty")
    return await service.search_and_download(
        query.strip(),
        file_type=file_type,
        max_files=max_files,
        save_dir=save_dir,
    )


@mcp.tool()
def web_capabilities() -> dict:
    """Return machine-readable capabilities for PIHU's capability registry."""
    return {
        "name": "pihu-web-search-mcp",
        "online": True,
        "network_required": True,
        "supports": ["search", "fetch", "search_and_read", "download_file", "search_and_download"],
        "browser_required": False,
        "max_results": settings.max_results,
    }


async def _shutdown() -> None:
    await service.close()


def main() -> None:
    mcp.run()
