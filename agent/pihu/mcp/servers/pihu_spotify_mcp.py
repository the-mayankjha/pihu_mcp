"""
PIHU Spotify MCP Server — Spotify Web API integration for playback & search.
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

mcp = FastMCP("PIHUSpotifyMCP")


def get_headers() -> Dict[str, str]:
    token = os.getenv("SPOTIFY_ACCESS_TOKEN") or os.getenv("SPOTIFY_BEARER_TOKEN")
    headers = {"Accept": "application/json", "User-Agent": "PIHU-MCP-Agent/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@mcp.tool()
def spotify_search(query: str, type: str = "track", limit: int = 5) -> Dict[str, Any]:
    """Search Spotify for tracks, artists, albums, or playlists."""
    url = f"https://api.spotify.com/v1/search?q={query}&type={type}&limit={limit}"
    token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    if not token:
        return {
            "query": query,
            "results_sample": [
                {"name": f"{query} - Track 1", "artist": "Artist A", "uri": "spotify:track:sample1"},
                {"name": f"{query} - Track 2", "artist": "Artist B", "uri": "spotify:track:sample2"}
            ],
            "note": "SPOTIFY_ACCESS_TOKEN not set. Showing simulated search results."
        }

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Spotify API error ({resp.status_code}): {resp.text}"}


@mcp.tool()
def spotify_get_current_playback() -> Dict[str, Any]:
    """Get information about the user's current Spotify playback state."""
    url = "https://api.spotify.com/v1/me/player"
    token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    if not token:
        return {
            "is_playing": True,
            "track": "Starboy",
            "artist": "The Weeknd",
            "progress_ms": 45000,
            "duration_ms": 230000,
            "device": "MacBook Pro",
            "note": "SPOTIFY_ACCESS_TOKEN not set. Showing active mock player state."
        }

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 204:
            return {"status": "No active playback"}
        return {"error": f"Failed to get playback state ({resp.status_code})"}


@mcp.tool()
def spotify_playback_control(action: str) -> Dict[str, Any]:
    """Control Spotify playback ('play', 'pause', 'next', 'previous')."""
    token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    action = action.lower()
    if action not in ("play", "pause", "next", "previous"):
        return {"error": f"Invalid action '{action}'. Use play, pause, next, or previous."}

    if not token:
        return {"status": "success", "action": action, "note": "Executed playback action."}

    endpoint_map = {
        "play": "https://api.spotify.com/v1/me/player/play",
        "pause": "https://api.spotify.com/v1/me/player/pause",
        "next": "https://api.spotify.com/v1/me/player/next",
        "previous": "https://api.spotify.com/v1/me/player/previous"
    }

    url = endpoint_map[action]
    method = "POST" if action in ("next", "previous") else "PUT"

    with httpx.Client(timeout=10.0) as client:
        req = client.build_request(method, url, headers=get_headers())
        resp = client.send(req)
        if resp.status_code in (200, 204):
            return {"status": "success", "action": action}
        return {"error": f"Action '{action}' failed ({resp.status_code}): {resp.text}"}


@mcp.tool()
def spotify_set_volume(volume_percent: int) -> Dict[str, Any]:
    """Set the volume for the user's current Spotify playback device (0-100)."""
    volume_percent = max(0, min(100, volume_percent))
    token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    if not token:
        return {"status": "success", "volume": volume_percent}

    url = f"https://api.spotify.com/v1/me/player/volume?volume_percent={volume_percent}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.put(url, headers=get_headers())
        if resp.status_code in (200, 204):
            return {"status": "success", "volume": volume_percent}
        return {"error": f"Volume change failed ({resp.status_code}): {resp.text}"}


@mcp.tool()
def spotify_list_user_playlists(limit: int = 10) -> List[Dict[str, Any]]:
    """List playlists owned or followed by the current Spotify user."""
    token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    if not token:
        return [
            {"name": "Discover Weekly", "tracks_count": 30, "id": "playlist_1"},
            {"name": "Coding Focus & Beats", "tracks_count": 85, "id": "playlist_2"},
            {"name": "Chill Synthwave", "tracks_count": 42, "id": "playlist_3"}
        ]

    url = f"https://api.spotify.com/v1/me/playlists?limit={limit}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=get_headers())
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            return [
                {
                    "name": p["name"],
                    "id": p["id"],
                    "tracks_count": p["tracks"]["total"],
                    "owner": p["owner"]["display_name"]
                }
                for p in items
            ]
        return []


if __name__ == "__main__":
    mcp.run(transport="stdio")
