from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GoogleMCP")

@mcp.tool()
def gmail_search(query: str) -> List[Dict[str, Any]]:
    """Search user's Gmail messages for a query."""
    return [
        {
            "id": "msg_001",
            "subject": f"Sample message matching '{query}'",
            "sender": "example@domain.com",
            "snippet": "This is a simulated message snippet for query: " + query
        }
    ]

@mcp.tool()
def gmail_draft(recipient: str, subject: str, body: str) -> Dict[str, str]:
    """Create a draft email in Gmail."""
    return {
        "status": "draft_created",
        "recipient": recipient,
        "subject": subject,
        "id": "draft_99"
    }

@mcp.tool()
def calendar_list() -> List[Dict[str, str]]:
    """List upcoming Google Calendar events."""
    return [
        {"title": "Team Sync", "start": "2026-09-10T10:00:00Z", "end": "2026-09-10T10:30:00Z"},
        {"title": "PIHU Architecture Review", "start": "2026-09-10T14:00:00Z", "end": "2026-09-10T15:00:00Z"}
    ]

if __name__ == "__main__":
    mcp.run(transport="stdio")
