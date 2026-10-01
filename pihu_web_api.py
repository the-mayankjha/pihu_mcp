"""
pihu-web MCP Registry Backend REST API (FastAPI / Standard Python WSGI).
Serves package catalog, search, manifests, and version metadata for https://pihu.nfks.co.in/api/v1/mcp/
"""

import json
from typing import Dict, Any, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

CATALOG_PACKAGES = [
    {
        "id": "google-workspace",
        "name": "google-workspace",
        "version": "1.2.0",
        "displayName": "Google Workspace MCP",
        "category": "Productivity",
        "description": "Gmail send/search, Google Calendar, Drive search, Docs editor & Sheets",
        "author": "PIHU Community",
        "runtime": "python",
        "transport": "stdio",
        "installCmd": "pihu mcp install google-workspace",
        "toolsProvided": ["gmail_search", "gmail_send", "calendar_list_events", "drive_search", "docs_create", "sheets_read"],
        "prereqs": "Python 3.10+ & Google OAuth Credentials",
        "configSnippet": "{\n  \"google-workspace\": {\n    \"command\": \"python\",\n    \"args\": [\"-m\", \"mcp_server_google_workspace\"]\n  }\n}"
    },
    {
        "id": "github",
        "name": "github",
        "version": "1.1.0",
        "displayName": "GitHub Integration MCP",
        "category": "Developer Tools",
        "description": "Create PRs, issues, read commits, workflows, and search repository code",
        "author": "Model Context Protocol",
        "runtime": "python",
        "transport": "stdio",
        "installCmd": "pihu mcp install github",
        "toolsProvided": ["github_search_repositories", "github_get_repository", "github_list_issues", "github_create_issue", "github_list_pull_requests"],
        "prereqs": "GitHub Personal Access Token (GITHUB_TOKEN)",
        "configSnippet": "{\n  \"github\": {\n    \"command\": \"python\",\n    \"args\": [\"pihu_github_mcp.py\"]\n  }\n}"
    },
    {
        "id": "spotify",
        "name": "spotify",
        "version": "1.0.0",
        "displayName": "Spotify Player & Search MCP",
        "category": "Media",
        "description": "Spotify track & playlist search, playback control, volume adjust & current playing track",
        "author": "PIHU Community",
        "runtime": "python",
        "transport": "stdio",
        "installCmd": "pihu mcp install spotify",
        "toolsProvided": ["spotify_search", "spotify_get_current_playback", "spotify_playback_control", "spotify_set_volume"],
        "prereqs": "Spotify Premium & SPOTIFY_ACCESS_TOKEN",
        "configSnippet": "{\n  \"spotify\": {\n    \"command\": \"python\",\n    \"args\": [\"pihu_spotify_mcp.py\"]\n  }\n}"
    },
    {
        "id": "sqlite",
        "name": "sqlite",
        "version": "1.0.0",
        "displayName": "SQLite Database MCP",
        "category": "Database",
        "description": "Query, introspect, and execute SQL across local SQLite databases",
        "author": "Model Context Protocol",
        "runtime": "python",
        "transport": "stdio",
        "installCmd": "pihu mcp install sqlite",
        "toolsProvided": ["read_query", "write_query", "create_table", "list_tables", "describe_table"],
        "prereqs": "Python 3.10+ (pip)",
        "configSnippet": "{\n  \"sqlite\": {\n    \"command\": \"python\",\n    \"args\": [\"-m\", \"mcp_server_sqlite\", \"--db-path\", \"./app.db\"]\n  }\n}"
    },
    {
        "id": "docker",
        "name": "docker",
        "version": "1.0.1",
        "displayName": "Docker Engine MCP",
        "category": "DevOps & Cloud",
        "description": "Inspect, start, stop containers, view container logs, and manage images",
        "author": "PIHU Community",
        "runtime": "python",
        "transport": "stdio",
        "installCmd": "pihu mcp install docker",
        "toolsProvided": ["list_containers", "start_container", "stop_container", "get_logs", "list_images"],
        "prereqs": "Docker Daemon running locally",
        "configSnippet": "{\n  \"docker\": {\n    \"command\": \"python\",\n    \"args\": [\"-m\", \"mcp_server_docker\"]\n  }\n}"
    }
]


class PihuWebMCPHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for /api/v1/mcp/ REST endpoints."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path in ("/api/v1/mcp/catalog", "/api/v1/mcp/", "/api/v1/mcp/packages"):
            res = json.dumps(CATALOG_PACKAGES, indent=2)
            self.wfile.write(res.encode("utf-8"))
            return

        if path.startswith("/api/v1/mcp/search"):
            q = query.get("q", [""])[0].lower()
            filtered = [p for p in CATALOG_PACKAGES if q in p["id"] or q in p["description"].lower()]
            res = json.dumps({"total": len(filtered), "results": filtered}, indent=2)
            self.wfile.write(res.encode("utf-8"))
            return

        if "/packages/" in path:
            parts = path.rstrip("/").split("/")
            pkg_id = parts[-1]
            for p in CATALOG_PACKAGES:
                if p["id"] == pkg_id:
                    self.wfile.write(json.dumps(p, indent=2).encode("utf-8"))
                    return

        # Fallback 404
        self.wfile.write(json.dumps({"error": "Endpoint or package not found"}, indent=2).encode("utf-8"))


def run_api_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), PihuWebMCPHandler)
    print(f"PIHU Web MCP Registry API running at http://0.0.0.0:{port}/api/v1/mcp/catalog")
    server.serve_forever()


if __name__ == "__main__":
    run_api_server()
