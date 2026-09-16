# PIHU Web Search MCP

A fast, structured, HTTP-first Web MCP for PIHU.

## Design

- MCP Python SDK v2
- `uv` project
- async `httpx`
- provider abstraction
- typed Pydantic responses
- SSRF-aware URL validation
- redirect validation
- content extraction with Trafilatura + BeautifulSoup
- TTL search cache
- concurrent multi-source retrieval
- offline capability metadata
- stdio transport by default

## Tools

- `web_search`
- `web_fetch`
- `web_search_and_read`
- `web_capabilities`

## Run

```bash
uv sync
cp .env.example .env
uv run web-search-mcp
```

Set `BRAVE_SEARCH_API_KEY` before using `web_search`.

## Development

```bash
uv run pytest
uv run ruff check .
uv run mcp dev web_search_mcp/server.py
```

The browser layer is intentionally optional. Add Playwright later for pages that require JavaScript rendering; keep HTTP/API retrieval as the fast path.
