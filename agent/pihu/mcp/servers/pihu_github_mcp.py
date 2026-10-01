"""
PIHU GitHub MCP Server — Full-featured GitHub REST API integration.
"""

import os
import httpx
from typing import List, Dict, Any, Optional
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except ImportError:
        from mcp.server import FastMCP

mcp = FastMCP("PIHUGitHubMCP")


def get_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "PIHU-MCP-Agent/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@mcp.tool()
def github_search_repositories(query: str, sort: str = "stars", limit: int = 5) -> List[Dict[str, Any]]:
    """Search GitHub repositories by query string (e.g. 'language:python topic:mcp')."""
    url = f"https://api.github.com/search/repositories?q={query}&sort={sort}&per_page={limit}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            return [
                {
                    "full_name": item["full_name"],
                    "stars": item["stargazers_count"],
                    "forks": item["forks_count"],
                    "language": item.get("language"),
                    "url": item["html_url"],
                    "description": item.get("description", "")
                }
                for item in items
            ]
        return []


@mcp.tool()
def github_get_repository(owner: str, repo: str) -> Dict[str, Any]:
    """Get full details of a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            data = resp.json()
            return {
                "full_name": data["full_name"],
                "stars": data["stargazers_count"],
                "default_branch": data["default_branch"],
                "open_issues": data["open_issues_count"],
                "license": data.get("license", {}).get("name") if data.get("license") else None,
                "description": data.get("description", ""),
                "html_url": data["html_url"]
            }
        return {"error": f"Failed to fetch repository ({resp.status_code}): {resp.text}"}


@mcp.tool()
def github_list_issues(owner: str, repo: str, state: str = "open", limit: int = 5) -> List[Dict[str, Any]]:
    """List issues for a given GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state={state}&per_page={limit}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return [
                {
                    "number": item["number"],
                    "title": item["title"],
                    "state": item["state"],
                    "author": item["user"]["login"],
                    "created_at": item["created_at"],
                    "url": item["html_url"]
                }
                for item in resp.json()
                if "pull_request" not in item
            ]
        return []


@mcp.tool()
def github_create_issue(owner: str, repo: str, title: str, body: str = "") -> Dict[str, Any]:
    """Create a new issue in a GitHub repository (Requires GITHUB_TOKEN)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=get_headers(), json={"title": title, "body": body})
        if resp.status_code == 201:
            data = resp.json()
            return {"status": "created", "number": data["number"], "url": data["html_url"]}
        return {"status": "error", "message": resp.text}


@mcp.tool()
def github_list_pull_requests(owner: str, repo: str, state: str = "open", limit: int = 5) -> List[Dict[str, Any]]:
    """List pull requests for a given GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state={state}&per_page={limit}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return [
                {
                    "number": item["number"],
                    "title": item["title"],
                    "author": item["user"]["login"],
                    "head": item["head"]["ref"],
                    "base": item["base"]["ref"],
                    "url": item["html_url"]
                }
                for item in resp.json()
            ]
        return []


@mcp.tool()
def github_get_file_contents(owner: str, repo: str, path: str, ref: str = "main") -> Dict[str, Any]:
    """Get raw contents of a file from a GitHub repository."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return {"path": path, "content": resp.text[:5000], "truncated": len(resp.text) > 5000}
        return {"error": f"Failed to fetch file content ({resp.status_code})"}


@mcp.tool()
def github_list_commits(owner: str, repo: str, limit: int = 5) -> List[Dict[str, Any]]:
    """List recent commits in a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page={limit}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return [
                {
                    "sha": item["sha"][:7],
                    "author": item["commit"]["author"]["name"],
                    "message": item["commit"]["message"].split("\n")[0],
                    "date": item["commit"]["author"]["date"]
                }
                for item in resp.json()
            ]
        return []


if __name__ == "__main__":
    mcp.run(transport="stdio")
