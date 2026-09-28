import os
import httpx
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GitHubMCP")

def get_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

@mcp.tool()
def search_repositories(query: str) -> List[Dict[str, Any]]:
    """Search GitHub repositories by query string."""
    url = f"https://api.github.com/search/repositories?q={query}&per_page=5"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            return [
                {
                    "full_name": item["full_name"],
                    "stars": item["stargazers_count"],
                    "url": item["html_url"],
                    "description": item.get("description", "")
                }
                for item in items
            ]
        return []

@mcp.tool()
def list_issues(owner: str, repo: str) -> List[Dict[str, Any]]:
    """List open issues for a given GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page=10"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return [
                {
                    "number": item["number"],
                    "title": item["title"],
                    "author": item["user"]["login"],
                    "created_at": item["created_at"]
                }
                for item in resp.json()
            ]
        return []

@mcp.tool()
def create_issue(owner: str, repo: str, title: str, body: str = "") -> Dict[str, Any]:
    """Create a new issue in a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=get_headers(), json={"title": title, "body": body})
        if resp.status_code == 201:
            data = resp.json()
            return {"status": "created", "number": data["number"], "url": data["html_url"]}
        return {"status": "error", "message": resp.text}

if __name__ == "__main__":
    mcp.run(transport="stdio")
