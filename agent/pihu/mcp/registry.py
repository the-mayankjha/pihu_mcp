"""
Registry Client for PIHU MCP Package Ecosystem (pihu.nfks.co.in/api/v1/mcp).
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from pihu.mcp.manifest import MCPPackageManifest

DEFAULT_REGISTRY_URL = os.getenv("PIHU_MCP_REGISTRY_URL", "https://pihu.nfks.co.in/api/v1/mcp")


class MCPRegistryClient:
    """Communicates with the official PIHU MCP Registry REST API."""

    def __init__(self, base_url: str = DEFAULT_REGISTRY_URL, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search(self, query: str = "", category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search the remote registry for packages matching a query or category."""
        params = {}
        if query:
            params["q"] = query
        if category:
            params["category"] = category

        url = f"{self.base_url}/search"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PIHU-MCP-Installer/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("results", [])
        except Exception:
            pass

        # Built-in fallback search index when offline or registry unreachable
        return self._builtin_fallback_search(query)

    async def get_package_info(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        """Fetch package metadata for a specific package ID."""
        url = f"{self.base_url}/packages/{mcp_id}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PIHU-MCP-Installer/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        return self._builtin_package_info(mcp_id)

    async def fetch_manifest(self, mcp_id: str, version: str = "latest") -> MCPPackageManifest:
        """Retrieve and parse the MCPPackageManifest for a package ID and version."""
        url = f"{self.base_url}/packages/{mcp_id}/versions/{version}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PIHU-MCP-Installer/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return MCPPackageManifest.from_dict(data)
        except Exception:
            pass

        # Fallback to local manifest builder
        info = self._builtin_package_info(mcp_id)
        if info:
            return MCPPackageManifest.from_dict(info)

        raise ValueError(f"Package '{mcp_id}' not found in registry ({self.base_url}).")

    def _builtin_fallback_search(self, query: str) -> List[Dict[str, Any]]:
        catalog = [
            {
                "id": "google-workspace",
                "name": "google-workspace",
                "version": "1.2.0",
                "description": "Gmail, Google Calendar, Drive, Docs & Sheets integration",
                "category": "Productivity",
                "runtime": "python",
                "author": "PIHU Community",
                "tools_count": 10,
            },
            {
                "id": "sqlite",
                "name": "sqlite",
                "version": "1.0.0",
                "description": "Query and introspect local SQLite databases",
                "category": "Database",
                "runtime": "python",
                "author": "Model Context Protocol",
                "tools_count": 5,
            },
            {
                "id": "github",
                "name": "github",
                "version": "1.1.0",
                "description": "Create PRs, issues, commits and search repository code",
                "category": "Developer Tools",
                "runtime": "node",
                "author": "Model Context Protocol",
                "tools_count": 6,
            },
            {
                "id": "docker",
                "name": "docker",
                "version": "1.0.1",
                "description": "Container inspection, logs and local docker daemon runner",
                "category": "DevOps",
                "runtime": "python",
                "author": "PIHU Community",
                "tools_count": 6,
            },
            {
                "id": "slack",
                "name": "slack",
                "version": "1.0.0",
                "description": "Post messages, search channels and monitor threads",
                "category": "Productivity",
                "runtime": "node",
                "author": "PIHU Community",
                "tools_count": 5,
            },
        ]
        if not query:
            return catalog
        q = query.lower()
        return [c for c in catalog if q in c["id"].lower() or q in c["description"].lower()]

    def _builtin_package_info(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        packages = {
            "google-workspace": {
                "schema_version": 1,
                "id": "google-workspace",
                "name": "google-workspace",
                "version": "1.2.0",
                "description": "Gmail, Google Calendar, Drive, Docs & Sheets integration",
                "runtime": "python",
                "transport": "stdio",
                "installation": {
                    "method": "pip",
                    "package": "mcp-server-google-workspace"
                },
                "entrypoint": {
                    "command": "python",
                    "args": ["-m", "mcp_server_google_workspace"]
                },
                "permissions": {
                    "network": True,
                    "env_vars_required": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
                },
                "tools_provided": [
                    "gmail_search", "gmail_send", "calendar_list_events",
                    "drive_search_files", "docs_create", "sheets_read"
                ]
            },
            "sqlite": {
                "schema_version": 1,
                "id": "sqlite",
                "name": "sqlite",
                "version": "1.0.0",
                "description": "SQLite Database MCP",
                "runtime": "python",
                "transport": "stdio",
                "installation": {
                    "method": "pip",
                    "package": "mcp-server-sqlite"
                },
                "entrypoint": {
                    "command": "python",
                    "args": ["-m", "mcp_server_sqlite", "--db-path", "./app.db"]
                },
                "tools_provided": ["read_query", "write_query", "list_tables", "describe_table"]
            },
            "github": {
                "schema_version": 1,
                "id": "github",
                "name": "github",
                "version": "1.1.0",
                "description": "GitHub Integration MCP",
                "runtime": "node",
                "transport": "stdio",
                "installation": {
                    "method": "npm",
                    "package": "@modelcontextprotocol/server-github"
                },
                "entrypoint": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"]
                },
                "permissions": {
                    "network": True,
                    "env_vars_required": ["GITHUB_PERSONAL_ACCESS_TOKEN"]
                },
                "tools_provided": ["create_issue", "create_pull_request", "get_file_contents", "list_commits"]
            }
        }
        return packages.get(mcp_id.lower())
