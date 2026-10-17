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
            res = gapi.list_calendar_events(max_results=max_results, time_min=time_min)
            return res.get("events", [])
        except Exception as e:
            raise RuntimeError(str(e))
    raise RuntimeError("Google API client unavailable")

@mcp.tool()
def calendar_create_event(
    summary: str, 
    start_time: str, 
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
            res = gapi.list_tasks(show_completed=show_completed)
            return res.get("tasks", [])
        except Exception as e:
            raise RuntimeError(str(e))
    raise RuntimeError("Google API client unavailable")

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
def docs_create(title: str, content: str = "") -> Dict[str, Any]:
    """Create a real Google Doc via Google Docs API."""
    if gapi:
        try:
            return gapi.create_doc(title=title, content=content)
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
            raise RuntimeError(str(e))
    raise RuntimeError("Google API client unavailable")

# Additional workspace tools. Resource identifiers are URL-encoded, never used as URLs.
from urllib.parse import quote, urlencode
import base64

def _api(url, method="GET", data=None):
    if not gapi:
        raise RuntimeError("Google client is unavailable. Repair Google Workspace MCP.")
    return gapi.make_google_api_request(url, method=method, data=data)

def _id(value):
    if not value or len(value) > 2048:
        raise ValueError("A valid resource ID is required")
    return quote(value, safe="")

@mcp.tool()
def docs_read(document_id: str) -> Dict[str, Any]:
    """Read a Google document including its text, structure and revision ID."""
    return _api(f"https://docs.googleapis.com/v1/documents/{_id(document_id)}")

@mcp.tool()
def docs_append(document_id: str, text: str, revision_id: Optional[str] = None) -> Dict[str, Any]:
    """Append reviewed text to a document. Supply revision_id to reject concurrent edits."""
    body = {"requests": [{"insertText": {"endOfSegmentLocation": {}, "text": text}}]}
    if revision_id:
        body["writeControl"] = {"requiredRevisionId": revision_id}
    return _api(f"https://docs.googleapis.com/v1/documents/{_id(document_id)}:batchUpdate", "POST", body)

@mcp.tool()
def docs_replace_text(document_id: str, find: str, replacement: str, match_case: bool = True) -> Dict[str, Any]:
    """Replace matching document text, preserving the rest of the document."""
    if not find:
        raise ValueError("Search text cannot be empty")
    return _api(f"https://docs.googleapis.com/v1/documents/{_id(document_id)}:batchUpdate", "POST", {"requests": [{"replaceAllText": {"containsText": {"text": find, "matchCase": match_case}, "replaceText": replacement}}]})

@mcp.tool()
def drive_get_file(file_id: str) -> Dict[str, Any]:
    """Read Drive file metadata and its browser URL."""
    return _api(f"https://www.googleapis.com/drive/v3/files/{_id(file_id)}?fields=id,name,mimeType,webViewLink,parents,modifiedTime,size")

@mcp.tool()
def drive_create_folder(name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a Drive folder, optionally inside another folder."""
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    return _api("https://www.googleapis.com/drive/v3/files?fields=id,name,webViewLink", "POST", body)

@mcp.tool()
def drive_upload_text(name: str, content: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """Upload UTF-8 text or Markdown as a Drive file, optionally to a folder."""
    # Create metadata, then upload content to that same ID.
    body = {"name": name, "mimeType": "text/plain"}
    if parent_id:
        body["parents"] = [parent_id]
    created = _api("https://www.googleapis.com/drive/v3/files?fields=id,name,webViewLink", "POST", body)
    try:
        gapi.make_google_api_request(f"https://www.googleapis.com/upload/drive/v3/files/{_id(created['id'])}?uploadType=media", method="PATCH", headers={"Content-Type": "text/plain; charset=utf-8"}, data=content)
    except Exception as error:
        return {"error": str(error), "partial_file_id": created.get("id"), "message": "File metadata created but content upload failed; do not repeat blindly."}
    return created

@mcp.tool()
def drive_move_file(file_id: str, destination_folder_id: str) -> Dict[str, Any]:
    """Move a Drive file into a destination folder, removing its previous parent folders."""
    current = drive_get_file(file_id)
    query = {"addParents": destination_folder_id, "fields": "id,name,parents,webViewLink"}
    if current.get("parents"):
        query["removeParents"] = ",".join(current["parents"])
    return _api(f"https://www.googleapis.com/drive/v3/files/{_id(file_id)}?{urlencode(query)}", "PATCH", {})

@mcp.tool()
def drive_share_file(file_id: str, email: str, role: str = "reader", confirmed: bool = False) -> Dict[str, Any]:
    """Share a specific file with a user. Requires explicit confirmation; role reader/commenter/writer."""
    if not confirmed or role not in ("reader", "commenter", "writer"):
        raise ValueError("Confirm the recipient and permitted sharing role first")
    return _api(f"https://www.googleapis.com/drive/v3/files/{_id(file_id)}/permissions", "POST", {"type": "user", "role": role, "emailAddress": email})

@mcp.tool()
def drive_trash_file(file_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Move a Drive file to Trash, never permanently delete it. Requires user confirmation."""
    if not confirmed:
        raise ValueError("Ask the user to confirm moving this file to Trash")
    return _api(f"https://www.googleapis.com/drive/v3/files/{_id(file_id)}", "PATCH", {"trashed": True})

@mcp.tool()
def sheets_create(title: str) -> Dict[str, Any]:
    """Create a Google spreadsheet and return its ID and URL."""
    return _api("https://sheets.googleapis.com/v4/spreadsheets", "POST", {"properties": {"title": title}})

@mcp.tool()
def sheets_read(spreadsheet_id: str, range_a1: str) -> Dict[str, Any]:
    """Read cells using A1 notation, for example Sheet1!A1:D20."""
    return _api(f"https://sheets.googleapis.com/v4/spreadsheets/{_id(spreadsheet_id)}/values/{_id(range_a1)}")

@mcp.tool()
def sheets_write(spreadsheet_id: str, range_a1: str, values: List[List[str]], append: bool = False) -> Dict[str, Any]:
    """Write rows of literal cell values (RAW), or append rows. Does not evaluate untrusted formulas."""
    path = f"https://sheets.googleapis.com/v4/spreadsheets/{_id(spreadsheet_id)}/values/{_id(range_a1)}"
    return _api(path + (":append" if append else "") + "?valueInputOption=RAW", "POST" if append else "PUT", {"values": values})

@mcp.tool()
def slides_create(title: str) -> Dict[str, Any]:
    """Create an empty Google Slides presentation."""
    return _api("https://slides.googleapis.com/v1/presentations", "POST", {"title": title})

@mcp.tool()
def slides_read(presentation_id: str) -> Dict[str, Any]:
    """Read slides, text elements and object IDs in a presentation."""
    return _api(f"https://slides.googleapis.com/v1/presentations/{_id(presentation_id)}")

@mcp.tool()
def slides_add_text_slide(presentation_id: str, title: str, body: str) -> Dict[str, Any]:
    """Append a title and body slide to a Google Slides presentation."""
    import uuid
    slide, heading, text = ["pihu_" + uuid.uuid4().hex for _ in range(3)]
    requests = [{"createSlide": {"objectId": slide, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]
    for object_id, content, top, height in [(heading, title, 30, 60), (text, body, 110, 260)]:
        requests.extend([{"createShape": {"objectId": object_id, "shapeType": "TEXT_BOX", "elementProperties": {"pageObjectId": slide, "size": {"width": {"magnitude": 640, "unit": "PT"}, "height": {"magnitude": height, "unit": "PT"}}, "transform": {"scaleX": 1, "scaleY": 1, "translateX": 40, "translateY": top, "unit": "PT"}}}}, {"insertText": {"objectId": object_id, "text": content}}])
    return _api(f"https://slides.googleapis.com/v1/presentations/{_id(presentation_id)}:batchUpdate", "POST", {"requests": requests})

@mcp.tool()
def calendar_update_event(event_id: str, summary: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """Update an event on the primary calendar. Times must be RFC3339 with timezone offsets."""
    body = {}
    for key, value in [("summary", summary), ("description", description)]:
        if value is not None:
            body[key] = value
    for key, value in [("start", start), ("end", end)]:
        if value is not None:
            body[key] = {"dateTime": value}
    if not body:
        raise ValueError("No event changes supplied")
    return _api(f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{_id(event_id)}", "PATCH", body)

@mcp.tool()
def calendar_delete_event(event_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Delete a primary-calendar event after explicit user confirmation."""
    if not confirmed:
        raise ValueError("Confirm event deletion first")
    _api(f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{_id(event_id)}", "DELETE")
    return {"deleted": True, "event_id": event_id}

@mcp.tool()
def tasks_update_task(task_id: str, title: Optional[str] = None, notes: Optional[str] = None, completed: Optional[bool] = None) -> Dict[str, Any]:
    """Edit or complete a Google Task in the default task list."""
    body = {}
    if title is not None: body["title"] = title
    if notes is not None: body["notes"] = notes
    if completed is not None: body["status"] = "completed" if completed else "needsAction"
    if not body: raise ValueError("No task changes supplied")
    return _api(f"https://tasks.googleapis.com/tasks/v1/lists/@default/tasks/{_id(task_id)}", "PATCH", body)

@mcp.tool()
def tasks_delete_task(task_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Delete a task after explicit user confirmation."""
    if not confirmed: raise ValueError("Confirm task deletion first")
    _api(f"https://tasks.googleapis.com/tasks/v1/lists/@default/tasks/{_id(task_id)}", "DELETE")
    return {"deleted": True, "task_id": task_id}

@mcp.tool()
def docs_format(document_id: str, start_index: int, end_index: int, style: str) -> Dict[str, Any]:
    """Format a document range as heading1, heading2, heading3, normal, bold or italic. Indices are Google Docs UTF-16 indices (body starts at 1)."""
    if start_index < 1 or end_index <= start_index:
        raise ValueError("Invalid document range")
    span = {"startIndex": start_index, "endIndex": end_index}
    styles = {"heading1": "HEADING_1", "heading2": "HEADING_2", "heading3": "HEADING_3", "normal": "NORMAL_TEXT"}
    if style in styles:
        request = {"updateParagraphStyle": {"range": span, "paragraphStyle": {"namedStyleType": styles[style]}, "fields": "namedStyleType"}}
    elif style in ("bold", "italic"):
        request = {"updateTextStyle": {"range": span, "textStyle": {style: True}, "fields": style}}
    else:
        raise ValueError("Unsupported text style")
    return _api(f"https://docs.googleapis.com/v1/documents/{_id(document_id)}:batchUpdate", "POST", {"requests": [request]})

if __name__ == "__main__":
    mcp.run()
