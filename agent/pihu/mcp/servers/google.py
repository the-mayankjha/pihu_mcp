from typing import List, Dict, Any, Optional
import os
import json
import datetime
from mcp.server.fastmcp import FastMCP

# Try importing real Google API client helper
try:
    from . import google_api_client as gapi
except ImportError:
    try:
        import google_api_client as gapi
    except ImportError:
        gapi = None

mcp = FastMCP("GoogleWorkspaceMCP")

# ─── GMAIL TOOLS ──────────────────────────────────────────────────────────────

@mcp.tool()
def gmail_search(query: str = "is:unread", max_results: int = 5) -> Dict[str, Any]:
    """Search user's real Gmail messages for a query string."""
    if gapi:
        try:
            return gapi.search_gmail(query=query, max_results=max_results)
        except Exception as e:
            return {"error": f"Gmail search API error: {str(e)}", "messages": []}
    return {"error": "Google API client module unavailable", "messages": []}

@mcp.tool()
def gmail_check_unread() -> Dict[str, Any]:
    """Check for unread Gmail messages using real Gmail API."""
    if gapi:
        try:
            return gapi.search_gmail(query="is:unread", max_results=5)
        except Exception as e:
            return {"has_unread": False, "unread_count": 0, "error": str(e)}
    return {"has_unread": False, "unread_count": 0}

@mcp.tool()
def gmail_send(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """Send a real email to a recipient via Gmail API."""
    if gapi:
        try:
            return gapi.send_gmail(recipient=recipient, subject=subject, body=body)
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return {"status": "error", "error": "Google API client unavailable"}

@mcp.tool()
def gmail_get_message(message_id: str) -> Dict[str, Any]:
    """Get full details and content of a specific Gmail message by ID."""
    if gapi:
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
            return gapi.make_google_api_request(url)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Google API client unavailable"}

# ─── GOOGLE CALENDAR TOOLS ───────────────────────────────────────────────────

@mcp.tool()
def calendar_list(time_min: Optional[str] = None, max_results: int = 5) -> List[Dict[str, Any]]:
    """List upcoming real Google Calendar events."""
    if gapi:
        try:
            res = gapi.list_calendar_events(max_results=max_results)
            return res.get("events", [])
        except Exception as e:
            return []
    return []

@mcp.tool()
def calendar_create_event(
    summary: str, 
    start_time: str = "", 
    end_time: str = "", 
    description: str = "", 
    location: str = ""
) -> Dict[str, Any]:
    """Create a new event on Google Calendar with a real Google Meet video call link."""
    if gapi:
        try:
            return gapi.create_calendar_event(summary=summary, start_time=start_time, end_time=end_time, description=description)
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return {"status": "error", "error": "Google API client unavailable"}

# ─── GOOGLE TASKS TOOLS ───────────────────────────────────────────────────────

@mcp.tool()
def tasks_list_tasks(show_completed: bool = False) -> List[Dict[str, Any]]:
    """List tasks from real Google Tasks API."""
    if gapi:
        try:
            res = gapi.list_tasks()
            return res.get("tasks", [])
        except Exception as e:
            return []
    return []

@mcp.tool()
def tasks_create_task(title: str, due: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
    """Create a task in Google Tasks."""
    if gapi:
        try:
            return gapi.create_task(title=title, due=due, notes=notes)
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return {"status": "error", "error": "Google API client unavailable"}

# ─── GOOGLE DOCS & DRIVE TOOLS ───────────────────────────────────────────────

@mcp.tool()
def docs_create(title: str) -> Dict[str, Any]:
    """Create a real Google Doc via Google Docs API."""
    if gapi:
        try:
            return gapi.create_doc(title=title)
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return {"status": "error", "error": "Google API client unavailable"}

@mcp.tool()
def drive_search(query: str = "") -> List[Dict[str, Any]]:
    """Search files in Google Drive."""
    if gapi:
        try:
            res = gapi.search_drive(query=query)
            return res.get("files", [])
        except Exception as e:
            return []
    return []

if __name__ == "__main__":
    mcp.run()
