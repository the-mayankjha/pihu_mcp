import sys
import os
import json
import ssl
import subprocess
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
        with open(TOKEN_PATH, "r") as f:
            data = json.load(f)
        refresh_token = data.get("refresh_token")
        if not refresh_token and data.get("current_user"):
            refresh_token = data["current_user"].get("refresh_token")
        if not refresh_token:
            return None

        client_id = data.get("client_id") or os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = data.get("client_secret") or os.environ.get("GOOGLE_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            for cpath in [
                os.path.expanduser("~/.gworkspace-mcp/credentials.json"),
                os.path.expanduser("~/.config/google-workspace-mcp/credentials.json")
            ]:
                if os.path.exists(cpath):
                    try:
                        with open(cpath, "r") as f:
                            c_data = json.load(f).get("installed", {})
                            if not client_id:
                                client_id = c_data.get("client_id", "")
                            if not client_secret:
                                client_secret = c_data.get("client_secret", "")
                    except Exception:
                        pass

        if not client_id or not client_secret:
            print("Token refresh error: Missing client_id or client_secret. Please re-link account in Settings.", file=sys.stderr)
            return None

        token_url = "https://oauth2.googleapis.com/token"
        post_data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }).encode("utf-8")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(token_url, data=post_data, headers={"Content-Type": "application/x-www-form-urlencoded"})

        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            token_resp = json.loads(resp.read().decode("utf-8"))
            new_access_token = token_resp.get("access_token")
            if new_access_token:
                data["access_token"] = new_access_token
                data["client_id"] = client_id
                data["client_secret"] = client_secret
                if "current_user" in data and isinstance(data["current_user"], dict):
                    data["current_user"]["access_token"] = new_access_token
                curr_email = data.get("current_user", {}).get("email") if isinstance(data.get("current_user"), dict) else None
                if "accounts" in data and isinstance(data["accounts"], list):
                    for acc in data["accounts"]:
                        if curr_email and acc.get("email") == curr_email:
                            acc["access_token"] = new_access_token
                with open(TOKEN_PATH, "w") as f_out:
                    json.dump(data, f_out, indent=2)
                return new_access_token
    except Exception as e:
        print(f"Token refresh failed: {e}", file=sys.stderr)
    return None

def make_google_api_request(url, method="GET", headers=None, data=None, retry_on_401=True):
    access_token, refresh_token = get_tokens()
    if not access_token:
        raise Exception("No active Google OAuth access token found. Please link your account in Settings.")

    if headers is None:
        headers = {}
    headers["Authorization"] = f"Bearer {access_token}"

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        body_bytes = None
        if data is not None:
            if isinstance(data, dict):
                body_bytes = json.dumps(data).encode("utf-8")
                headers["Content-Type"] = "application/json"
            elif isinstance(data, str):
                body_bytes = data.encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as http_err:
        if http_err.code == 401 and retry_on_401:
            new_token = refresh_access_token()
            if new_token:
                return make_google_api_request(url, method=method, headers=headers, data=data, retry_on_401=False)
        try:
            err_text = http_err.read().decode("utf-8")
            err_json = json.loads(err_text)
            err_msg = err_json.get("error", {}).get("message") or err_text
            if "has not been used in project" in err_msg or "disabled" in err_msg:
                raise Exception(f"Google API Disabled (HTTP 403): {err_msg}")
            raise Exception(f"HTTP Error {http_err.code}: {err_msg}")
        except Exception as read_err:
            if "HTTP Error" in str(read_err) or "Google API Disabled" in str(read_err):
                raise read_err
            raise http_err
    except Exception as e:
        try:
            curl_cmd = ["curl", "-s", "-X", method, url, "-H", f"Authorization: Bearer {access_token}"]
            if data is not None:
                if isinstance(data, dict):
                    curl_cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
                elif isinstance(data, str):
                    curl_cmd.extend(["-d", data])
            
            res = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout) if res.stdout else {}
        except Exception as e2:
            raise Exception(f"Google API request to {url} failed: {str(e2)}")
            raise Exception(f"Google API request to {url} failed: {str(e2)}")

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

def list_calendar_events(max_results=5):
    now_iso = datetime.utcnow().isoformat() + "Z"
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
    
    if not start_time:
        now = datetime.utcnow() + timedelta(hours=1)
        start_time = now.isoformat() + "Z"
        end_time = (now + timedelta(hours=1)).isoformat() + "Z"

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
    meet_url = resp.get("hangoutLink") or f"https://meet.google.com/{resp.get('id', 'pihu')}"

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

def list_tasks():
    url = "https://tasks.googleapis.com/tasks/v1/users/@me/lists/@default/tasks?showCompleted=false"
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
    url = "https://tasks.googleapis.com/tasks/v1/users/@me/lists/@default/tasks"
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

def create_doc(title):
    url = "https://docs.googleapis.com/v1/documents"
    resp = make_google_api_request(url, method="POST", data={"title": title})
    doc_id = resp.get("documentId")
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
