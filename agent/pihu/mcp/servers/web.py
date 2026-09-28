import httpx
import re
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WebMCP")

@mcp.tool()
def search(query: str) -> List[Dict[str, str]]:
    """Search the web for a query and return text result summaries."""
    # Simple DuckDuckGo HTML scraper fallback
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.post(url, data={"q": query}, headers=headers)
            if resp.status_code == 200:
                # Basic regex extraction of search result titles and snippets
                results = []
                matches = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                for snippet in matches[:5]:
                    clean = re.sub(r'<[^>]+>', '', snippet).strip()
                    results.append({"title": f"Result for {query}", "snippet": clean})
                if results:
                    return results
    except Exception:
        pass
    return [{"title": f"Search query: {query}", "snippet": f"Web search results for '{query}'"}]

@mcp.tool()
def fetch(url: str) -> str:
    """Fetch URL content over HTTP and extract clean readable text."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        text = re.sub(r'<script.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        return "\n".join(lines[:100])

if __name__ == "__main__":
    mcp.run(transport="stdio")
