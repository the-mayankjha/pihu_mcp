import sys
import os
import json
import ssl
import urllib.parse
import urllib.request
import base64
from datetime import datetime, timedelta

TOKEN_PATH = os.path.expanduser("~/.gemini/antigravity/google_workspace_tokens.json")

def get_tokens():
    if not os.path.exists(TOKEN_PATH):
        return None, None
    try:
        with open(TOKEN_PATH, "r") as f:
            data = json.load(f)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not access_token and isinstance(data.get("current_user"), dict):
            access_token = data["current_user"].get("access_token")
        if not refresh_token and isinstance(data.get("current_user"), dict):
            refresh_token = data["current_user"].get("refresh_token")
        return access_token, refresh_token
    except Exception:
        return None, None

def refresh_access_token():
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        refresh_token = data.get("refresh_token")
        if not refresh_token and isinstance(data.get("current_user"), dict):
            refresh_token = data["current_user"].get("refresh_token")
        if not refresh_token:
            return None

        request_body = json.dumps({"refresh_token": refresh_token}).encode("utf-8")
        request = urllib.request.Request(
            "https://pihu.nfks.co.in/api/v2/oauth/google/refresh",
            data=request_body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=20) as response:
                token_response = json.loads(response.read().decode("utf-8"))
        except Exception:
            # If the hosted broker is down, refresh fallback credentials directly
            # with Google using the OAuth client already configured on this device.
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")
            if not client_id or not client_secret:
                raise
            form = urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }).encode("ascii")
            local_request = urllib.request.Request(
                "https://oauth2.googleapis.com/token", data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            )
            with urllib.request.urlopen(local_request, context=ssl.create_default_context(), timeout=20) as response:
                token_response = json.loads(response.read().decode("utf-8"))
        new_access_token = token_response.get("access_token")
        if not new_access_token:
            return None
        data["access_token"] = new_access_token
        if isinstance(data.get("current_user"), dict):
            data["current_user"]["access_token"] = new_access_token
        email = data.get("current_user", {}).get("email") if isinstance(data.get("current_user"), dict) else None
        for account in data.get("accounts", []):
            if email and account.get("email", "").lower() == email.lower():
                account["access_token"] = new_access_token
        with open(TOKEN_PATH, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.chmod(TOKEN_PATH, 0o600)
        return new_access_token
    except Exception as error:
        print(f"Token refresh failed: {error}", file=sys.stderr)
        return None

def make_google_api_request(url, method="GET", headers=None, data=None, retry_on_401=True):
    access_token, _refresh_token = get_tokens()
    if not access_token:
        raise Exception("No active Google OAuth access token found. Please link your account in Settings.")

    request_headers = dict(headers or {})
    request_headers["Authorization"] = f"Bearer {access_token}"
    body_bytes = None
    if data is not None:
        if isinstance(data, dict):
            body_bytes = json.dumps(data).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        elif isinstance(data, str):
            body_bytes = data.encode("utf-8")

    request = urllib.request.Request(url, data=body_bytes, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=20) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as error:
        if error.code == 401 and retry_on_401:
            new_token = refresh_access_token()
            if new_token:
                return make_google_api_request(url, method=method, headers=headers, data=data, retry_on_401=False)
        try:
            error_text = error.read().decode("utf-8")
            error_json = json.loads(error_text)
            message = error_json.get("error", {}).get("message") or error_text
            if "has not been used in project" in message or "disabled" in message:
                raise Exception(f"Google API Disabled (HTTP 403): {message}")
            raise Exception(f"HTTP Error {error.code}: {message}")
        except (json.JSONDecodeError, AttributeError):
            raise error

# ── GMAIL ───────────────────────────────────────────────────────────────────

def search_gmail(query="is:unread", max_results=10):
    try:
        max_results = int(max_results)
    except Exception:
        max_results = 10

    encoded_query = urllib.parse.quote(query)
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={encoded_query}&maxResults={max_results}"
    resp = make_google_api_request(url)
    
    result_size_estimate = resp.get("resultSizeEstimate", 0)
    messages = resp.get("messages", [])
    if not messages:
        return {
            "has_unread": False,
            "count": 0,
            "total_estimated": 0,
            "messages": [],
            "message": f"No emails matching '{query}' were found in your Gmail inbox, Sir."
        }

    results = []
    for msg in messages[:max_results]:
        msg_id = msg["id"]
        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"
        msg_detail = make_google_api_request(detail_url)
        
        payload = msg_detail.get("payload", {})
        headers_list = payload.get("headers", [])
        
        subject = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "No Subject")
        sender = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "Unknown Sender")
        date_str = next((h["value"] for h in headers_list if h["name"].lower() == "date"), "")
        snippet = msg_detail.get("snippet", "")

        results.append({
            "id": msg_id,
            "subject": subject,
            "sender": sender,
            "date": date_str,
            "snippet": snippet
        })

    total_count = max(result_size_estimate, len(results))
    latest = results[0] if results else None
    prompt_str = f"You have {total_count} total unread email(s) in your Gmail inbox, Sir. The latest email is from {latest['sender']} with subject '{latest['subject']}'. Would you like me to read out the full body for any specific email, Sir?" if latest else "No unread emails, Sir."

    return {
        "has_unread": True,
        "count": len(results),
        "total_estimated": total_count,
        "messages": results,
        "latest_email": latest,
        "prompt": prompt_str,
        "message": f"You have {total_count} unread email(s) in your Gmail inbox, Sir. Showing the latest {len(results)}."
    }

def send_gmail(recipient, subject, body):
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    raw_str = f"To: {recipient}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
    raw_b64 = base64.urlsafe_b64encode(raw_str.encode("utf-8")).decode("utf-8")
    
    resp = make_google_api_request(url, method="POST", data={"raw": raw_b64})
    return {
        "status": "sent",
        "recipient": recipient,
        "subject": subject,
        "message_id": resp.get("id"),
        "message": f"Successfully sent email to {recipient} via Gmail API."
    }

# ── CALENDAR ─────────────────────────────────────────────────────────────────

def list_calendar_events(max_results=5, time_min=None):
    now_iso = time_min or datetime.utcnow().isoformat() + "Z"
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={urllib.parse.quote(now_iso)}&maxResults={max_results}&singleEvents=true&orderBy=startTime"
    resp = make_google_api_request(url)
    
    items = resp.get("items", [])
    events = []
    for item in items:
        start_time = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
        end_time = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
        meet_link = item.get("hangoutLink") or item.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", "")

        events.append({
            "id": item.get("id"),
            "summary": item.get("summary", "No Title"),
            "start": start_time,
            "end": end_time,
            "location": item.get("location", "No location"),
            "hangoutLink": meet_link,
            "organizer": item.get("organizer", {}).get("email", "")
        })

    return {
        "count": len(events),
        "events": events,
        "message": f"Fetched {len(events)} upcoming event(s) from your Google Calendar."
    }

def create_calendar_event(summary, start_time=None, end_time=None, description=""):
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1"
    
    if not start_time or "T" not in start_time:
        raise ValueError("Supply a meeting start date and time in RFC3339 format with a timezone offset")
    start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if start.tzinfo is None:
        raise ValueError("Meeting time must include a timezone offset")
    if not end_time:
        end_time = (start + timedelta(hours=1)).isoformat()
    end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    if end.tzinfo is None or end <= start:
        raise ValueError("Meeting end must include a timezone and be after its start")

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time if "T" in start_time else f"{start_time}T09:00:00Z"},
        "end": {"dateTime": end_time if "T" in end_time else f"{end_time}T10:00:00Z"},
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet_{int(datetime.now().timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    }

    resp = make_google_api_request(url, method="POST", data=event_body)
    meet_url = resp.get("hangoutLink") or next((item.get("uri") for item in resp.get("conferenceData", {}).get("entryPoints", []) if item.get("entryPointType") == "video"), "")

    return {
        "status": "created",
        "event_id": resp.get("id"),
        "summary": summary,
        "start": start_time,
        "end": end_time,
        "google_meet_url": meet_url,
        "html_link": resp.get("htmlLink", ""),
        "message": f"Successfully scheduled '{summary}' on Google Calendar with Google Meet link: {meet_url}"
    }

# ── TASKS ───────────────────────────────────────────────────────────────────

def list_tasks(show_completed=False):
    url = "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks?showCompleted=" + str(show_completed).lower()
    resp = make_google_api_request(url)
    
    items = resp.get("items", [])
    tasks = [{
        "id": t.get("id"),
        "title": t.get("title"),
        "due": t.get("due"),
        "status": t.get("status"),
        "notes": t.get("notes", "")
    } for t in items]

    return {
        "count": len(tasks),
        "tasks": tasks,
        "message": f"Fetched {len(tasks)} active task(s) from Google Tasks."
    }

def create_task(title, due=None, notes=""):
    url = "https://tasks.googleapis.com/tasks/v1/lists/@default/tasks"
    body = {"title": title, "notes": notes}
    if due:
        body["due"] = due if "T" in due else f"{due}T00:00:00.000Z"
        
    resp = make_google_api_request(url, method="POST", data=body)
    return {
        "status": "created",
        "task_id": resp.get("id"),
        "title": title,
        "due": due,
        "message": f"Created Google Task: '{title}'"
    }

# ── DOCS & DRIVE ─────────────────────────────────────────────────────────────

def create_doc(title, content=""):
    if not title.strip():
        return {"error": "Document title is required"}
    url = "https://docs.googleapis.com/v1/documents"
    resp = make_google_api_request(url, method="POST", data={"title": title})
    doc_id = resp.get("documentId")
    if not doc_id:
        return {"error": "Google did not return a document ID"}
    if content:
        try:
            make_google_api_request(f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate", method="POST", data={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]})
        except Exception as error:
            return {"error": str(error), "partial_document_id": doc_id, "doc_url": f"https://docs.google.com/document/d/{doc_id}/edit", "message": "Document created but content insertion failed. Do not create another document blindly."}
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return {
        "status": "created",
        "document_id": doc_id,
        "title": title,
        "doc_url": doc_url,
        "message": f"Created Google Doc '{title}': {doc_url}"
    }

def search_drive(query=""):
    url = f"https://www.googleapis.com/drive/v3/files?q=name+contains+'{urllib.parse.quote(query)}'&pageSize=5"
    resp = make_google_api_request(url)
    files = [{"id": f.get("id"), "name": f.get("name"), "mimeType": f.get("mimeType")} for f in resp.get("files", [])]
    return {
        "count": len(files),
        "files": files,
        "message": f"Found {len(files)} file(s) in Google Drive matching '{query}'"
    }

# ── CLI MAIN ENTRYPOINT ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command provided"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()
    try:
        if cmd == "search_gmail":
            q = sys.argv[2] if len(sys.argv) > 2 else "is:unread"
            res = search_gmail(query=q)
        elif cmd == "get_unread_emails":
            res = search_gmail(query="is:unread", max_results=5)
        elif cmd == "send_email":
            rec = sys.argv[2] if len(sys.argv) > 2 else ""
            sub = sys.argv[3] if len(sys.argv) > 3 else ""
            body = sys.argv[4] if len(sys.argv) > 4 else ""
            res = send_gmail(rec, sub, body)
        elif cmd == "list_calendar_events":
            res = list_calendar_events()
        elif cmd == "create_calendar_event":
            sum_str = sys.argv[2] if len(sys.argv) > 2 else "Meeting"
            start_str = sys.argv[3] if len(sys.argv) > 3 else None
            end_str = sys.argv[4] if len(sys.argv) > 4 else None
            desc_str = sys.argv[5] if len(sys.argv) > 5 else ""
            res = create_calendar_event(sum_str, start_str, end_str, desc_str)
        elif cmd == "list_tasks":
            res = list_tasks()
        elif cmd == "create_task":
            t_title = sys.argv[2] if len(sys.argv) > 2 else "New Task"
            t_due = sys.argv[3] if len(sys.argv) > 3 else None
            t_notes = sys.argv[4] if len(sys.argv) > 4 else ""
            res = create_task(t_title, t_due, t_notes)
        elif cmd == "create_doc":
            d_title = sys.argv[2] if len(sys.argv) > 2 else "Untitled Document"
            res = create_doc(d_title)
        elif cmd == "search_drive":
            dr_q = sys.argv[2] if len(sys.argv) > 2 else ""
            res = search_drive(dr_q)
        else:
            res = {"error": f"Unknown command: {cmd}"}

        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
